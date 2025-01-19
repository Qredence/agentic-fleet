# AgenticFleet Quickstart Example

This example demonstrates basic usage of AgenticFleet with both CLI and web interface implementations.

## Structure

```
quickstart/
├── README.md
├── requirements.txt
├── .env.example
├── cli_example.py
└── web_example.py
```

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

3. Run the examples:

CLI version:
```bash
python cli_example.py
```

Web version:
```bash
chainlit run web_example.py
```

## What's Included

- Basic agent team creation
- Message handling
- File operations
- Error handling examples
- Web interface setup
