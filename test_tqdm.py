import sys
from huggingface_hub import hf_hub_download

class TqdmInterceptor:
    def __init__(self, orig_stderr):
        self.orig = orig_stderr
        self.buf = ""
    def write(self, s):
        self.orig.write(s)
    def flush(self):
        self.orig.flush()
    def isatty(self):
        return True

sys.stderr = TqdmInterceptor(sys.stderr)
hf_hub_download(repo_id="gpt2", filename="model.safetensors", force_download=True)
