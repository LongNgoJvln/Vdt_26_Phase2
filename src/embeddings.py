"""
embeddings.py

Embedding clients for RAG and memory vector search.

Priority order:
  1. HTTP API (Ollama / vLLM / llama.cpp) — set EMBEDDING_URL in .env
  2. Local ONNX (onnxruntime) — loads LOCAL_EMBEDDING_PATH directly
  3. Local fastembed (ONNX, ~50MB) — legacy fallback

Set EMBEDDING_URL in .env, e.g.:
  EMBEDDING_URL=http://localhost:11434/v1/embeddings   (ollama)
  EMBEDDING_URL=http://localhost:8000/v1/embeddings    (vllm / llama.cpp)
"""

import os

# Windows: force HuggingFace to COPY model files rather than symlink
# them. On a network-share/UNC cache dir Windows can't follow HF's symlinks
# ([WinError 1463] "symbolic link cannot be followed"), so model loading fails
# and semantic memory dies. huggingface_hub reads this flag at import time,
# so it must be set before huggingface_hub is first imported — hence module-top.
# (app.py sets the same guard for the server entrypoint.)
if os.name == "nt":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Set tokenzier cache to data/ so downloads land in a persistent location
os.environ.setdefault("TOKENZIER_CACHE", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "tokenzier_cache",
))

import json
import logging
import numpy as np
import httpx
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "all-minilm:l6-v2"
_DEFAULT_SENTENCE_TRANSFORMERS_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingClient:
    """Drop-in replacement for SentenceTransformer.encode() using an HTTP API."""

    def __init__(self, url: Optional[str] = None, model: Optional[str] = None):
        self.url = url or os.getenv(
            "EMBEDDING_URL",
            f"http://{os.getenv('LLM_HOST', 'localhost')}:11434/v1/embeddings",
        )
        self.model = model or os.getenv("EMBEDDING_MODEL", _DEFAULT_MODEL)
        self._dim: Optional[int] = None
        # Short connect timeout so a DOWN embedding endpoint (e.g. Ollama not
        # running on :11434) fast-fails to the local FastEmbed fallback instead
        # of stalling startup ~30s per probe. Read stays generous for a real
        # endpoint (embedding a short string returns in well under a second).
        self._client = httpx.Client(timeout=httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=3.0))

    def get_sentence_embedding_dimension(self) -> int:
        """Probe the endpoint for embedding dimension if not yet known."""
        if self._dim is not None:
            return self._dim
        # Embed a single word to discover the dimension
        vec = self.encode(["hello"])
        self._dim = vec.shape[1]
        logger.info(f"Embedding dimension: {self._dim} (model={self.model})")
        return self._dim

    def encode(
        self, texts: List[str], normalize_embeddings: bool = True
    ) -> np.ndarray:
        """Encode texts via the API. Returns (N, dim) float32 array."""
        if not texts:
            return np.array([], dtype="float32")

        # Batch in chunks of 64 to avoid oversized requests
        all_vecs = []
        for i in range(0, len(texts), 64):
            batch = texts[i : i + 64]
            resp = self._client.post(
                self.url,
                json={"input": batch, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()

            # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
            embeddings = data.get("data", [])
            embeddings.sort(key=lambda e: e.get("index", 0))
            for emb in embeddings:
                all_vecs.append(emb["embedding"])

        vecs = np.array(all_vecs, dtype="float32")

        if normalize_embeddings and vecs.size > 0:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            vecs = vecs / norms

        if self._dim is None and vecs.size > 0:
            self._dim = vecs.shape[1]

        return vecs


class ONNXEmbeddingClient:
    """DEPRECATED — use HuggingFaceEmbeddingClient with LOCAL_EMBEDDING_PATH instead.
    Kept in code for reference but not wired into the factory."""
    pass


class HuggingFaceEmbeddingClient:
    """Local embedding client using huggingface transformers + torch directly.
    
    Independent of sentence-transformers (which can be broken in some Python versions).
    Works with any local model directory containing tokenizer and model files.
    
    Priority:
      1. HUGGINGFACE_LOCAL_PATH env var — load from a local model directory
      2. LOCAL_EMBEDDING_PATH — fallback env var name
      3. SENTENCE_TRANSFORMERS_MODEL — download from HF hub if needed
    """

    def __init__(self, model: Optional[str] = None):
        # Check for local model path
        local_path = os.getenv("HUGGINGFACE_LOCAL_PATH") or os.getenv("LOCAL_EMBEDDING_PATH")
        if local_path and os.path.isdir(local_path):
            self.model_name = local_path
            logger.info(f"Local embedding path set: {local_path}")
        else:
            self.model_name = model or os.getenv(
                "HUGGINGFACE_MODEL", _DEFAULT_SENTENCE_TRANSFORMERS_MODEL
            )
        
        # Try to load with transformers/torch directly first
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel
        except ImportError:
            raise RuntimeError(
                "transformers/torch not installed. Install with: pip install transformers torch"
            )
        
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = self._model.to(torch.device(device))
            self._model.eval()
            self._use_cuda = device == "cuda"
            # Get embedding dimension
            with torch.no_grad():
                test_input = self._tokenizer(["test"], return_tensors="pt")
                test_input = {k: v.to(self._model.device) for k, v in test_input.items()}
                out = self._model(**test_input)
                self._dim = out.last_hidden_state.shape[-1]
            
            logger.info(f"HuggingFace model loaded: {self.model_name} dim={self._dim}")
            self.url = f"local://huggingface/{self.model_name.split('/')[-1]}"
            return
        except Exception as e:
            logger.warning(f"Direct transformers load failed ({e}); falling back to sentence-transformers import")
        
        # Fallback to sentence-transformers (if import doesn't fail)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "Neither transformers directly nor sentence-transformers could load. "
                f"Error: {e}"
            ) from e
        
        self._st = SentenceTransformer(self.model_name)
        self._dim = self._st.get_sentence_embedding_dimension()
        self.url = f"local://sentence-transformers/{self.model_name.split('/')[-1]}"
        logger.info(f"SentenceTransformer loaded: {self.model_name}")

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim or 384

    def encode(
        self, texts: List[str], normalize_embeddings: bool = True
    ) -> np.ndarray:
        """Encode texts locally. Returns (N, dim) float32 array."""
        if not texts:
            return np.array([], dtype="float32")
        
        # Check if we're using sentence-transformers (has no _tokenizer attribute)
        if not hasattr(self, '_tokenizer'):
            from sentence_transformers import SentenceTransformer
            embeddings = self._st.encode(
                texts,
                normalize_embeddings=normalize_embeddings,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.astype("float32")
        
        import torch
        
        inputs = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self._model(**inputs)
        
        # Mean pooling
        attention_mask = inputs['attention_mask']
        last_hidden = outputs.last_hidden_state
        if attention_mask is not None:
            # Expand mask to match hidden size
            mask = attention_mask.unsqueeze(-1).float()
            sum_hidden = (last_hidden * mask).sum(dim=1)
            sum_mask = mask.sum(dim=1).clamp(min=1e-9)
            embeddings = sum_hidden / sum_mask
        else:
            embeddings = last_hidden.mean(dim=1)
        
        # L2 normalize (matches sentence-transformers behavior)
        if normalize_embeddings:
            norms = embeddings.norm(dim=1, keepdim=True)
            norms = torch.where(norms == 0, torch.ones_like(norms), norms)
            embeddings = embeddings / norms
        
        return embeddings.cpu().numpy().astype("float32")


# ONNX-only embedding client (no PyTorch / sentence-transformers needed)
class ONNXEmbeddingClient:
    """Local embedding using onnxruntime + tokenizers directly.

    Loads a model from LOCAL_EMBEDDING_PATH or HUGGINGFACE_LOCAL_PATH.
    No PyTorch, no CUDA, no HuggingFace hub downloads — pure ONNX on CPU.
    """

    def __init__(self, model: Optional[str] = None):
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as e:
            raise RuntimeError(
                "onnxruntime and tokenizers required for ONNX embedding. "
                "Install: pip install onnxruntime tokenizers"
            ) from e

        local_path = os.getenv("HUGGINGFACE_LOCAL_PATH") or os.getenv("LOCAL_EMBEDDING_PATH")
        if local_path and os.path.isdir(local_path):
            self.model_name = local_path
        else:
            self.model_name = model or os.getenv(
                "HUGGINGFACE_MODEL", _DEFAULT_SENTENCE_TRANSFORMERS_MODEL
            )
            if not os.path.isdir(self.model_name):
                raise RuntimeError(
                    f"LOCAL_EMBEDDING_PATH not set or invalid. "
                    f"Point it to a local model directory containing model.onnx + tokenizer.json"
                )

        # Find the ONNX file (onnx/ subdir or root)
        onnx_path = os.path.join(self.model_name, "onnx", "model.onnx")
        if not os.path.exists(onnx_path):
            onnx_path = os.path.join(self.model_name, "model.onnx")
        if not os.path.exists(onnx_path):
            raise RuntimeError(f"No model.onnx found under {self.model_name}/onnx/ or {self.model_name}/")

        # Load tokenizer
        tokenizer_path = os.path.join(self.model_name, "tokenizer.json")
        if not os.path.exists(tokenizer_path):
            raise RuntimeError(f"No tokenizer.json found at {tokenizer_path}")
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._tokenizer.enable_truncation(max_length=512)

        # Load ONNX model
        sess_options = onnxruntime.SessionOptions()
        sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = onnxruntime.InferenceSession(
            onnx_path, sess_options,
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._attn_name = self._session.get_inputs()[1].name if len(self._session.get_inputs()) > 1 else None
        # Collect all input names so we can provide them all
        self._input_names = [inp.name for inp in self._session.get_inputs()]

        # Infer dimension
        test_ids = [[0] * 4]
        test_feed = {self._input_name: test_ids}
        for name in self._input_names:
            if name != self._input_name:
                test_feed[name] = [[0] * 4]
        test_out = self._session.run(None, test_feed)
        self._dim = test_out[0].shape[-1]

        self.url = f"local://onnx/{os.path.basename(self.model_name)}"
        self.model = self.model_name  # alias for code expecting .model attribute
        logger.info(
            f"ONNX model loaded: {os.path.basename(self.model_name)} "
            f"dim={self._dim} provider=CPU"
        )

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim or 384

    def encode(self, texts, normalize_embeddings=True):
        """Encode texts. Returns (N, dim) float32 array."""
        import numpy as np
        if not texts:
            return np.array([], dtype="float32")

        encoding = self._tokenizer.encode_batch(texts)
        max_len = max(len(e.ids) for e in encoding) if encoding else 4
        max_len = min(max_len, 512)
        batch_size = len(texts)

        input_ids = np.zeros((batch_size, max_len), dtype=np.int64)
        attention_mask = np.zeros((batch_size, max_len), dtype=np.int64)
        for i, e in enumerate(encoding):
            ids = e.ids[:max_len]
            input_ids[i, :len(ids)] = ids
            attention_mask[i, :len(ids)] = 1

        feed = {self._input_name: input_ids}
        if self._attn_name:
            feed[self._attn_name] = attention_mask
        # Fill any remaining inputs (e.g. token_type_ids) with zeros
        for name in self._input_names:
            if name not in feed:
                feed[name] = np.zeros_like(input_ids)

        outputs = self._session.run(None, feed)
        embeddings = outputs[0]

        # Mean pooling
        mask_expanded = np.expand_dims(attention_mask, axis=-1)
        mask_expanded = np.broadcast_to(mask_expanded, embeddings.shape).astype(float)
        sum_embeddings = np.sum(embeddings * mask_expanded, axis=1)
        sum_mask = np.sum(mask_expanded, axis=1)
        sum_mask = np.clip(sum_mask, 1e-9, None)
        embeddings = sum_embeddings / sum_mask

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            embeddings = embeddings / norms

        return embeddings.astype("float32")


# Keep SentenceTransformerClient for backward compatibility
class SentenceTransformerClient:
    """DEPRECATED — use HuggingFaceEmbeddingClient instead.
    Kept for backward compatibility."""
    pass


class FastEmbedClient:
    """Local embedding client using fastembed (ONNX). No external service needed."""

    def __init__(self, model: Optional[str] = None):
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise RuntimeError(
                "Local fastembed is not installed. Either install it "
                "(pip install fastembed) or point the app at a remote "
                "embeddings server."
            ) from e

        self.model = model or os.getenv("FASTEMBED_MODEL", _DEFAULT_FASTEMBED_MODEL)
        # Persistent cache under data/ so the model survives reboots and so
        # the download lands exactly where the admin panel's _is_downloaded()
        # check looks (both default to this same path).
        cache_dir = os.getenv("FASTEMBED_CACHE_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "fastembed_cache",
        )
        os.makedirs(cache_dir, exist_ok=True)
        # Windows self-heal: the HuggingFace-hub cache stores model files as
        # symlinks (snapshots/<rev>/model.onnx -> ../../blobs/<hash>). On a
        # network-share / UNC data dir Windows refuses to follow them
        # ([WinError 1463] "symbolic link cannot be followed because its type is
        # disabled"), and a cache copied between machines can carry dead symlinks
        # too. Either way fastembed tries to load a broken symlink and fails
        # *without* re-downloading, leaving semantic memory degraded. Detect a
        # broken-symlink model in the cache and drop the contaminated hub dir so
        # fastembed re-fetches (it falls back to its CDN tarball of real files,
        # which load fine). Best-effort; only ever removes a verifiably dead link.
        if os.name == "nt":
            try:
                import glob, shutil
                for _onnx in glob.glob(os.path.join(cache_dir, "**", "*.onnx"), recursive=True):
                    if os.path.islink(_onnx) and not os.path.exists(_onnx):
                        _root = _onnx
                        while os.path.basename(_root) and not os.path.basename(_root).startswith("models--"):
                            _parent = os.path.dirname(_root)
                            if _parent == _root:
                                break
                            _root = _parent
                        if os.path.basename(_root).startswith("models--"):
                            logger.warning(
                                "Embedding cache has a broken symlink (%s); clearing %s "
                                "so fastembed re-downloads real files", _onnx, _root,
                            )
                            shutil.rmtree(_root, ignore_errors=True)
            except Exception as _e:
                logger.debug("embedding cache symlink-heal skipped: %s", _e)
        kwargs = {"model_name": self.model, "cache_dir": cache_dir}
        try:
            self._embedding = TextEmbedding(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load fastembed model '{self.model}' from cache. "
                f"Is the model cached at: {cache_dir}? "
                f"Error: {e}"
            ) from e
        self._dim: Optional[int] = None
        self.url = "local://fastembed"
        logger.info(f"FastEmbed loaded model={self.model}")

    def get_sentence_embedding_dimension(self) -> int:
        if self._dim is not None:
            return self._dim
        vec = self.encode(["hello"])
        self._dim = vec.shape[1]
        logger.info(f"Embedding dimension: {self._dim} (model={self.model})")
        return self._dim

    def encode(
        self, texts: List[str], normalize_embeddings: bool = True
    ) -> np.ndarray:
        """Encode texts locally. Returns (N, dim) float32 array."""
        if not texts:
            return np.array([], dtype="float32")

        vecs = np.array(list(self._embedding.embed(texts)), dtype="float32")

        if normalize_embeddings and vecs.size > 0:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            vecs = vecs / norms

        if self._dim is None and vecs.size > 0:
            self._dim = vecs.shape[1]

        return vecs


def _load_persisted_endpoint() -> dict:
    """Load the custom embedding endpoint saved from the admin panel."""
    try:
        endpoint_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "embedding_endpoint.json",
        )
        if os.path.exists(endpoint_file):
            import json
            data = json.loads(open(endpoint_file, encoding="utf-8").read())
            if data.get("url"):
                return data
    except Exception:
        pass
    return {}


_http_embed_down = False  # process-level latch: skip re-probing a dead endpoint


def reset_http_embed_state():
    """Clear the 'HTTP embedding endpoint is down' latch so the next
    get_embedding_client() re-probes. Call this when the embedding endpoint
    setting changes (e.g. the user starts Ollama and saves the endpoint) —
    otherwise a latch tripped at startup would keep us on FastEmbed for the
    whole process even after the endpoint comes back."""
    global _http_embed_down
    _http_embed_down = False


def get_embedding_client():
    """Factory: try HTTP API first, fall back to local ST, then fastembed."""
    global _http_embed_down

    # Check for a persisted custom endpoint (saved from admin panel)
    persisted = _load_persisted_endpoint()
    if persisted.get("url"):
        url = persisted["url"]
        model = persisted.get("model", "")
        # Also set in env so other code sees it
        os.environ["EMBEDDING_URL"] = url
        if model:
            os.environ["EMBEDDING_MODEL"] = model

    # Try the HTTP embedding API — unless we already found it down this process
    # (avoids paying the connect timeout again on every RAG/memory/tool probe).
    if not _http_embed_down:
        try:
            client = EmbeddingClient()
            client.get_sentence_embedding_dimension()  # health check
            logger.info(f"Using HTTP embedding API: {client.url} model={client.model}")
            return client
        except Exception as e:
            _http_embed_down = True
            logger.warning(f"HTTP embedding API unavailable ({e}); using local embedding for the rest of this process")

    # FALLBACK 1: Try ONNX-only embedding (no PyTorch needed)
    try:
        client = ONNXEmbeddingClient()
        client.get_sentence_embedding_dimension()
        logger.info(f"Using ONNX local model: {client.model_name}")
        return client
    except ImportError:
        logger.debug("onnxruntime or tokenizers not installed")
    except Exception as e:
        logger.warning(f"ONNX embedding init failed ({e}); trying HuggingFace")

    # FALLBACK 2: Try HuggingFace embedding (preferred when torch works)
    try:
        client = HuggingFaceEmbeddingClient()
        client.get_sentence_embedding_dimension()
        logger.info(f"Using HuggingFace local model: {client.model_name}")
        return client
    except ImportError:
        logger.debug("transformers/torch not installed — no local embedding available")
    except Exception as e:
        err_msg = str(e)
        # PyTorch with missing CUDA libs (GPU wheel on a no-CUDA host) raises
        # a hard ValueError at import time. Don't fall through to fastembed,
        # which tries to download from HF hub and hangs with no internet.
        if "not found in the system path" in err_msg or "libcublas" in err_msg or "libcudart" in err_msg:
            logger.warning(
                "PyTorch cannot load CUDA libraries — no local embedding. "
                "Set EMBEDDING_URL in .env to use an external embedding API."
            )
            return None
        logger.warning(f"HuggingFace init failed ({e}); no local embedding available")

    return None
