let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3.pkgs.pyyaml
    pkgs.python3.pkgs.markdown
    pkgs.python3.pkgs.python-markdown-math
  ];
}
