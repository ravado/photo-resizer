# 📷 Photo Resizer

A lightweight Python application for resizing and managing photos.  
Designed to make it easy to scale images, store metadata, and plan image operations with minimal setup.

---

## ✨ Features
- Resize images to predefined dimensions
- Simple configuration (`config.py`)
- Database operations for tracking processed files
- Modular design (`converter.py`, `imaging.py`, `planner.py`)
- Ready to extend for automation or integration into pipelines

---

## 📂 Project Structure

```
photo-resizer/
├── app/ # Core package
│ ├── init.py
│ ├── config.py # Configuration settings
│ ├── converter.py # Image resizing logic
│ ├── database_operations.py # Database helpers
│ ├── imaging.py # Low-level image operations
│ └── planner.py # Planning batch operations
├── app.py # Entry point script
├── requirements.txt # Python dependencies
└── README.md # Project documentation
```

---

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ravado/photo-resizer.git
   cd photo-resizer
   ```

2. Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate   # Linux/macOS
    venv\Scripts\activate      # Windows
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```


---

## 🚀 Usage

Run the application:
```bash
python app.py
```

Example (adjust when you add CLI options):
```bash
python app.py --input ./photos --output ./resized --width 1920 --height 1080
```

---

## 🛠 Configuration

Edit app/config.py to adjust:
- Default input/output directories
- Target image sizes
- Database connection settings

## 🗄 Database

The module database_operations.py handles storing information about processed images.
You can extend this to log operations, track duplicates, or integrate with external storage.