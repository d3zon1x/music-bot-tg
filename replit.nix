{ pkgs }: {
  deps = [
    pkgs.python312      # or python310, etc., depending on which version you want
    pkgs.ffmpeg        # ffmpeg for audio/video processing
    pkgs.pkg-config
    pkgs.libffi
    pkgs.zlib
    pkgs.openssl
  ];
}