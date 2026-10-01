# P4PNodeGossiper
P4PNodeGossiper is a wrapper around the P4PCore's gossip module, P4PCore.impledPlugin.Gossiper, specifically designed for node information sharing.
Gossip operations are performed non-encrypted based on P4PCore's Gossiper.

## Installation
This project depends on P4PCore. Refer to the [P4PCore repository](https://github.com/stsaria/P4PCore) for installation instructions.

The versions required can be found in this repository's `pyproject.toml`.

**pyproject.toml**
```toml
[project]
dependencies = [
    "P4PCore==<coreVersion>",
    "P4PNodeGossiper==<nodeGossiperVersion>"
]
```

Since these programs are not available on repositories like PyPI, download them from git.

```bash
pip install git+https://github.com/stsaria/P4PCore.git@<coreVersion>
pip install git+https://github.com/stsaria/P4PNodeGossiper.git@<nodeGossiperVersion>
pip install .
```