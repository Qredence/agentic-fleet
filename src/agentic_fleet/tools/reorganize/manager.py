import os
import shutil
from pathlib import Path


def reorganize_files():
    # Base paths
    src_dir = Path("src/agentic_fleet")

    # Create new directory structure
    dirs_to_create = [
        "apps/chainlit_ui/agent_registry",
        "apps/chainlit_ui/components",
        "core/agents",
        "core/config",
        "core/application",
        "shared/message_processing",
        "shared/utils",
    ]

    for dir_path in dirs_to_create:
        full_path = src_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        (full_path / "__init__.py").touch()

    # File movements
    file_moves = [
        ("app.py", "apps/chainlit_ui/app.py"),
        ("agent_registry.py", "apps/chainlit_ui/agent_registry/default_agents.py"),
        ("message_processing.py", "shared/message_processing/processors.py"),
        ("config_utils.py", "core/config/utils.py"),
        ("constants.py", "core/config/constants.py"),
        ("logging_config.py", "core/config/logging.py"),
        ("backend/application_manager.py", "core/application/app_manager.py"),
        ("@llm_config.yaml", "core/config/llm_config.yaml"),
        ("model_config.yaml", "core/config/model_config.yaml"),
        ("main.py", "main.py"),
    ]

    # Move files
    for src_file, dest_path in file_moves:
        src_path = src_dir / src_file
        dest_full_path = src_dir / dest_path
        if src_path.exists():
            print(f"Moving {src_path} to {dest_full_path}")
            shutil.move(str(src_path), str(dest_full_path))

    # Clean up unnecessary files
    files_to_remove = [
        "fleet1.py",
        "magentic_one_helper.py",
        ".DS_Store",
        "app.py",
    ]

    for file_name in files_to_remove:
        file_path = src_dir / file_name
        if file_path.exists():
            print(f"Removing {file_path}")
            file_path.unlink()

    # Remove empty directories
    for root, dirs, files in os.walk(str(src_dir), topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                dir_path.rmdir()  # Will only remove if empty
                print(f"Removed empty directory: {dir_path}")
            except OSError:
                pass  # Directory not empty


if __name__ == "__main__":
    reorganize_files()
