{
  description = "Bassic Python Flake";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs =
    {
      self,
      nixpkgs,
      flake-utils,

    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let

        pkgs = import nixpkgs {
          inherit system;

        };

      in
      {
        devShells = {
          # Native development - clean environment
          default = pkgs.mkShell {
            packages = [
              pkgs.python313
              pkgs.uv
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
              pkgs.ty
              pkgs.ruff
              pkgs.chromium
            ];
            shellHook = ''
                export LD_LIBRARY_PATH=$LD_LIBRARY_PATH${pkgs.zlib}/lib
                export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${pkgs.stdenv.cc.cc.lib}/lib
                export PATH=${pkgs.chromium}/bin:$PATH
              # Display current Python and uv versions
              echo "Python version: $(python --version)"
              echo "uv version: $(uv --version)"
              echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
              echo "UV_PYTHON: $UV_PYTHON"
              export UV_PYTHON=${pkgs.python313}/bin/python
              export UV_PYTHON_DOWNLOADS=never
              export UV_CACHE_DIR=$HOME/.cache/uv
              export UV_CACHE_DIR=$HOME/.cache/uv
            '';
          };

        };
      }
    );
}

