"""AgenticFleet Memory Manager - manages ChromaDB semantic memory."""

import argparse
import os
import shutil
import uuid
from datetime import datetime

from chroma_driver import ChromaDriver

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
RECALL_DIR = os.path.join(BASE_DIR, "recall")
CONFIG_TEMPLATE = os.path.join(BASE_DIR, ".chroma", "config.template.yaml")
CONFIG_FILE = os.path.join(BASE_DIR, ".chroma", "config.yaml")


def init_system(_):
    """Initialize the file-based memory system."""
    print("Initializing AgenticFleet Memory System...")

    # 1. Hydrate Core Templates
    templates = [
        ("project.template.md", "project.md"),
        ("human.template.md", "human.md"),
        ("persona.template.md", "persona.md"),
    ]

    for tmpl, dest in templates:
        src_path = os.path.join(CORE_DIR, tmpl)
        dest_path = os.path.join(CORE_DIR, dest)
        if not os.path.exists(dest_path):
            if os.path.exists(src_path):
                shutil.copy(src_path, dest_path)
                print(f"Created {dest} from template.")
            else:
                print(f"Warning: Template {tmpl} not found.")
        else:
            print(f"Skipped {dest} (already exists).")

    # 2. Config Setup
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(CONFIG_TEMPLATE):
            shutil.copy(CONFIG_TEMPLATE, CONFIG_FILE)
            print("Created config.yaml from template. PLEASE EDIT THIS FILE with your Chroma keys.")
        else:
            print("Warning: config.template.yaml not found.")

    # 3. Create Recall Scratchpad
    current_recall = os.path.join(RECALL_DIR, "current.md")
    if not os.path.exists(current_recall):
        # Create recall dir if not exists (handling missing dir)
        os.makedirs(RECALL_DIR, exist_ok=True)
        with open(current_recall, "w") as f:
            f.write(
                f"# Current Session Context\nCreated: {datetime.now()}\n\n## Active Task\n- [ ] ...\n"
            )
        print("Created recall/current.md")

    print("\nInitialization complete.")
    print(f"Please edit {CONFIG_FILE} to enable Chroma Cloud features.")
    print("\nNext step: Run 'setup-chroma' to create collections in Chroma Cloud.")


def setup_chroma(_):
    """Setup Chroma Cloud collections explicitly."""
    print("Setting up Chroma Cloud collections...")

    # Check config exists
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file not found at {CONFIG_FILE}")
        print("Run 'init' first, then edit the config file with your Chroma Cloud credentials.")
        return

    # Initialize driver (this creates collections via get_or_create)
    driver = ChromaDriver()

    if not driver.client:
        print("Error: Could not connect to Chroma Cloud.")
        print("Please check your API key and credentials in config.yaml")
        return

    # Verify collections were created
    print("\n=== Chroma Cloud Collections ===")
    for key, collection in driver.collections.items():
        try:
            count = collection.count()
            print(f"  {key}: {collection.name} ({count} documents)")
        except Exception as e:
            print(f"  {key}: Error getting count - {e}")

    print("\nChroma Cloud setup complete!")
    print("Collections are ready for use.")


def status_chroma(_):
    """Show status of Chroma Cloud collections."""
    print("Checking Chroma Cloud status...\n")

    # Check config
    if not os.path.exists(CONFIG_FILE):
        print("Config: NOT FOUND")
        print(f"  Expected at: {CONFIG_FILE}")
        print("  Run 'init' to create config from template.")
        return

    print(f"Config: {CONFIG_FILE}")

    # Try to connect
    driver = ChromaDriver()

    if not driver.client:
        print("Connection: FAILED")
        print("  Could not connect to Chroma Cloud.")
        print("  Check your API key in config.yaml")
        return

    print("Connection: OK")

    # Show collection status
    print("\n=== Collections ===")
    for key, collection in driver.collections.items():
        try:
            count = collection.count()
            print(f"  {key}:")
            print(f"    Name: {collection.name}")
            print(f"    Documents: {count}")
        except Exception as e:
            print(f"  {key}: Error - {e}")


def learn_skill(args):
    """Ingest a skill file into Chroma procedural memory."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        return

    # Read content
    with open(filepath) as f:
        content = f.read()

    # Simple parsing: Use filename as title if no # title found
    filename = os.path.basename(filepath)
    doc_id = f"skill_{filename}_{str(uuid.uuid4())[:8]}"

    driver = ChromaDriver()
    if not driver.client:
        print("Chroma not configured. Skipping cloud sync (file is saved locally).")
        return

    print(f"Learning skill from {filename}...")
    driver.add_memory(
        collection_type="procedural",
        documents=[content],
        metadatas=[{"source": filename, "type": "skill", "created": str(datetime.now())}],
        ids=[doc_id],
    )
    print("Skill successfully indexed in Chroma Cloud.")


def recall_memory(args):
    """Search memory for a query."""
    query = args.query
    driver = ChromaDriver()

    if not driver.client:
        print("Chroma not configured. Cannot perform semantic search.")
        return

    print(f"Searching memory for: '{query}'...")
    results = driver.query_all([query], n_results=3)

    # Format output for the Agent to read
    print("\n=== SEMANTIC RECALL RESULTS ===")

    for category, res in results.items():
        print(f"\n--- {category.upper()} ---")
        if not res or not res["documents"]:
            print("No relevant results.")
            continue

        for i, doc in enumerate(res["documents"][0]):
            meta = res["metadatas"][0][i] if res["metadatas"] else {}
            dist = res["distances"][0][i] if res["distances"] else "N/A"
            print(f"\n[Result {i + 1}] (Distance: {dist})")
            print(f"Source: {meta.get('source', 'unknown')}")
            print(f"Content Preview: {doc[:200]}..." if len(doc) > 200 else f"Content: {doc}")


def reflect_session(_):
    """Summarize and archive the current session."""
    current_recall = os.path.join(RECALL_DIR, "current.md")
    if not os.path.exists(current_recall):
        print("No active session found in recall/current.md")
        return

    # Create archive filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(RECALL_DIR, f"session_{timestamp}.md")

    # Move current to archive
    try:
        shutil.move(current_recall, archive_path)
        print(f"Session archived to {archive_path}")

        # Create fresh current.md
        with open(current_recall, "w") as f:
            f.write(
                f"# Current Session Context\nCreated: {datetime.now()}\n\n## Active Task\n- [ ] ...\n"
            )
        print("Reset recall/current.md for new session.")

        # Optional: Index to Chroma 'episodic' collection
        driver = ChromaDriver()
        if driver.client:
            with open(archive_path) as f:
                content = f.read()
            doc_id = f"session_{timestamp}"
            driver.add_memory(
                collection_type="episodic",
                documents=[content],
                metadatas=[
                    {
                        "source": "session_archive",
                        "type": "episodic",
                        "created": str(datetime.now()),
                    }
                ],
                ids=[doc_id],
            )
            print("Session indexed to episodic memory.")

    except Exception as e:
        print(f"Error during reflection: {e}")


def main():
    """Run memory manager CLI."""
    parser = argparse.ArgumentParser(description="AgenticFleet Memory Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init
    subparsers.add_parser("init", help="Initialize local memory files")

    # Setup Chroma
    subparsers.add_parser("setup-chroma", help="Setup Chroma Cloud collections")

    # Status
    subparsers.add_parser("status", help="Show Chroma Cloud status")

    # Learn
    learn_parser = subparsers.add_parser("learn", help="Learn a skill from a file")
    learn_parser.add_argument("--file", required=True, help="Path to markdown file")

    # Recall
    recall_parser = subparsers.add_parser("recall", help="Search memory")
    recall_parser.add_argument("query", help="Search query string")

    # Reflect
    subparsers.add_parser("reflect", help="Archive current session")

    args = parser.parse_args()

    if args.command == "init":
        init_system(args)
    elif args.command == "setup-chroma":
        setup_chroma(args)
    elif args.command == "status":
        status_chroma(args)
    elif args.command == "learn":
        learn_skill(args)
    elif args.command == "recall":
        recall_memory(args)
    elif args.command == "reflect":
        reflect_session(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
