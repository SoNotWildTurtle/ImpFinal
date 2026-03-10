Place GGUF models here.

`imp/bin/imp-install.sh` will attempt to download `starcoder2-15b.Q4_K_M.gguf` automatically. Set `IMP_GGUF_URL` to override the download source or `IMP_SKIP_GGUF_DOWNLOAD=1` to skip the step and provide your own file.

If you already have a full GGUF locally, set `IMP_GGUF_LOCAL_PATH` before install to copy it directly into `imp/models`:
`IMP_GGUF_LOCAL_PATH=/path/to/starcoder2-15b_Q4_K_M.gguf bash imp/bin/imp-install.sh`
