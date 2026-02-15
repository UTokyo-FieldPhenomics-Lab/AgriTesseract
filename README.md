# AgriTesseract 🌾🧊
> *Decoding the multi-dimensional matrix of agriculture through AI vision.*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Active_Development-orange)

## 🌌 Name Origin: Why "AgriTesseract"?

**Tesseract** (Hypercube) is a four-dimensional analogue of a cube.
Just as a Tesseract extends a 3D cube into a 4th dimension, **AgriTesseract** extends traditional 2D field phenotyping into higher dimensions:

1.  **Dimension X & Y (Space)**: Precise subplot segmentation and spatial mapping of every single plant in the field.
2. **Dimension Z (Depth/Health)**: Using **Custom 3D-CNN** to analyze stacked multi-modal layers (RGB + Multispectral + DSM), diving deeper than surface-level imagery.
3. **Dimension T (Time)**: Encoding growth stages into grayscale intensity layers, allowing the network to learn temporal sequences and detect growth anomalies.

In *Interstellar*, the Tesseract allowed access to time as a physical dimension. Similarly, **AgriTesseract** stacks time and spectrum into a 10-layer hypercube, enabling the detection of subtle growth abnormalities invisible to the naked eye.

---

## ✨ Key Features

### 1. Spatial Dimension: Subplot Pre-processing 🗺️
*   **Automated Grid Slicing**: Effortlessly slice massive orthomosaic maps into manageable subplots.
*   **Geo-Referencing**: Maintain precise GPS coordinates for every pixel.
*   **Ridge Detection**: Smart algorithms to identify crop rows and furrows automatically.

### 2. Identity Dimension: SAM3 Seedling Detection 🌱
*   **Zero-Shot Segmentation**: Powered by **Segment Anything Model 3 (SAM3)**, detecting seedlings without extensive retraining.
*   **Precise Localization**: Extract exact centroids and bounding boxes for every individual plant.
*   **ID Persistence**: Assign and track unique IDs for thousands of plants across the field.

### 3. Diagnostic Dimension: 4D Anomaly Detection (Spatiotemporal) 🧠
*   **Multi-Modal Stacking**: A novel approach stacking **RGB**, **Multispectral**, **DSM**, and **Temporal Growth Grayscale** into a unified 10-layer tensor.
*   **Temporal Learning**: The modified 3D-CNN learns the "normal" trajectory of plant growth across time sequences encoded in the input layers.
*   **Anomaly Scoring**: Identifies plants with deviant growth patterns (e.g., stunted growth, delayed emergence) by analyzing the reconstruction error of this hyper-dimensional data.

### 4. Observable Dimension: Interactive Visualization 👁️
*   **Modern GUI**: Built with **PySide6** and **QFluentWidgets** for a stunning, dark-mode focused experience.
*   **Data Export**: Seamlessly export results to shapefiles, CSVs, or visualize directly on Google Maps satellite layers.
*   **Real-time Plotting**: High-performance rendering of thousands of data points using `pyqtgraph`.

---

## 🖼️ UI Preview

*(Placeholders for future screenshots - Imagine a sleek, dark-themed interface with glowing green accents)*

| **Dashboard** | **Segmentation View** |
|:---:|:---:|
| ![Dashboard](docs/images/dashboard_placeholder.png) <br> *Overview of field metrics and project status* | ![SAM3 View](docs/images/sam3_placeholder.png) <br> *Real-time SAM3 inference on subplots* |

| **3D Analysis** | **Map Visualization** |
|:---:|:---:|
| ![3DCNN](docs/images/3dcnn_placeholder.png) <br> *3D-CNN feature space visualization* | ![Map](docs/images/map_placeholder.png) <br> *Geo-tagged results on satellite map* |

---

## 🛠️ Technology Stack

This project is built on the shoulders of giants:

*   **Core**: `Python 3.10+`
*   **GUI Framework**: `PySide6` (Qt for Python)
*   **UI Components**: `QFluentWidgets` (Windows 11 Fluent Design style)
*   **Computer Vision**: `Ultralytics (SAM3)`, `OpenCV`, `PyTorch`
*   **Data Science**: `NumPy`, `SciPy` (Signal Processing), `Pandas`, `GeoPandas`
*   **Visualization**: `PyQtGraph` (High-performance plotting)
*   **Testing**: `Pytest`

## 🚀 Getting Started

### Prerequisites

*   **OS**: Linux (Recommended) / Windows 11
*   **Package Manager**: `uv` (Fast Python package installer)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/UTokyo-FieldPhenomics-Lab/AgriTesseract.git
    cd AgriTesseract
    ```

2.  **Set up environment with `uv`**:
    ```bash
    # Create virtual environment and sync dependencies
    uv sync
    ```

3.  **Run the application**:
    ```bash
    uv run python launch.py
    ```

---

## 🤝 Contribution

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ and ☕ by UTokyo Field Phenomics Lab <br>
  <i>"Decoding nature, one pixel at a time."</i>
</p>
