"""Step 1: build train / test splits from the official DocILE labels (test = official val split)."""
import dl_common as d

if __name__ == "__main__":
    print(d.build_splits())
