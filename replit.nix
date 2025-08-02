{ pkgs }: {
  deps = [
    pkgs.python310Full
    pkgs.pip
    pkgs.rclone
    pkgs.curl
    pkgs.unzip
  ];
}
