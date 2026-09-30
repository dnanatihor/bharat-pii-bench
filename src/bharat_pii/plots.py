"""Confusion-matrix plots. Matplotlib ships without usable strict stubs here."""

from pathlib import Path

from bharat_pii.labels import Label


def plot_confusion(confusion: dict[tuple[Label, Label], int], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    labels = [label.value for label in Label]
    grid = [[confusion[(Label(row), Label(column))] for column in labels] for row in labels]
    figure, axes = plt.subplots(figsize=(10, 8))
    image = axes.imshow(grid)
    axes.set_xticks(range(len(labels)), labels, rotation=90)
    axes.set_yticks(range(len(labels)), labels)
    axes.set_xlabel("predicted")
    axes.set_ylabel("actual")
    figure.colorbar(image)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
