let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3.pkgs.pyyaml
    pkgs.python3.pkgs.markdown
    pkgs.python3.pkgs.python-markdown-math
    pkgs.python3.pkgs.graphviz
    pkgs.entr
    (pkgs.writeScriptBin "watch-algebra" ''
      #!${pkgs.stdenv.shell}
      find ./pages | entr sh -c "python build.py public/algebra < pages/algebra.yaml > public/algebra.html"
    '')
  ];
}
