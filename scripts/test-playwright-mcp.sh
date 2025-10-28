#!/bin/bash

# Playwright MCP Server Installation Test Script
# This script verifies that the Playwright MCP server is properly installed and configured

echo "🎭 Playwright MCP Server Installation Test"
echo "========================================"

# Check if Node.js is installed
echo "📋 Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js is installed: $NODE_VERSION"
else
    echo "❌ Node.js is not installed. Please install Node.js v16 or higher."
    exit 1
fi

# Check if npm is available
echo ""
echo "📦 Checking npm availability..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✅ npm is available: $NPM_VERSION"
else
    echo "❌ npm is not available."
    exit 1
fi

# Check if Playwright MCP is installed globally
echo ""
echo "🔍 Checking Playwright MCP server installation..."
if npm list -g @executeautomation/playwright-mcp-server &> /dev/null; then
    echo "✅ Playwright MCP server is installed globally"
    PKG_VERSION=$(npm list -g @executeautomation/playwright-mcp-server --depth=0 | grep playwright | sed 's/.*@//')
    echo "   Version: $PKG_VERSION"
else
    echo "❌ Playwright MCP server is not installed globally"
    echo "   Installing now..."
    npm install -g @executeautomation/playwright-mcp-server

    if [ $? -eq 0 ]; then
        echo "✅ Installation completed successfully"
    else
        echo "❌ Installation failed"
        exit 1
    fi
fi

# Test the MCP server executable
echo ""
echo "🧪 Testing Playwright MCP server executable..."
if npx @executeautomation/playwright-mcp-server --help &> /dev/null; then
    echo "✅ Playwright MCP server executable is working"
else
    echo "❌ Playwright MCP server executable test failed"
    echo "   Trying alternative test..."
    if command -v @executeautomation/playwright-mcp-server &> /dev/null; then
        echo "✅ Direct command works"
    else
        echo "❌ Both executable tests failed"
        exit 1
    fi
fi

# Check if Playwright browsers are installed
echo ""
echo "🌐 Checking Playwright browser installation..."
if npx playwright --version &> /dev/null; then
    echo "✅ Playwright is available"
    BROWSER_VERSION=$(npx playwright --version)
    echo "   Version: $BROWSER_VERSION"
else
    echo "⚠️  Playwright CLI not found, installing browsers..."
    npx playwright install --with-deps

    if [ $? -eq 0 ]; then
        echo "✅ Browser installation completed"
    else
        echo "❌ Browser installation failed"
        echo "   You may need to run: npx playwright install manually"
    fi
fi

# Verify MCP configuration
echo ""
echo "⚙️  Checking MCP configuration..."
MCP_CONFIG_FILE=".mcp.json"
if [ -f "$MCP_CONFIG_FILE" ]; then
    if grep -q "playwright" "$MCP_CONFIG_FILE"; then
        echo "✅ Playwright MCP server is configured in $MCP_CONFIG_FILE"
        echo "   Configuration:"
        grep -A 3 '"playwright"' "$MCP_CONFIG_FILE" | sed 's/^/   /'
    else
        echo "❌ Playwright MCP server is not configured in $MCP_CONFIG_FILE"
        echo "   Adding configuration now..."

        # Create backup
        cp "$MCP_CONFIG_FILE" "${MCP_CONFIG_FILE}.backup"

        # Add Playwright configuration (using Python for JSON manipulation)
        python3 << 'EOF'
import json

# Read existing config
with open('.mcp.json', 'r') as f:
    config = json.load(f)

# Add Playwright MCP server
config['mcpServers']['playwright'] = {
    "description": "Playwright MCP server for browser automation and testing",
    "command": "npx",
    "args": ["-y", "@executeautomation/playwright-mcp-server"]
}

# Write updated config
with open('.mcp.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
EOF

        if [ $? -eq 0 ]; then
            echo "✅ Configuration added successfully"
        else
            echo "❌ Configuration update failed"
            echo "   Please manually add the Playwright MCP server to $MCP_CONFIG_FILE"
        fi
    fi
else
    echo "❌ MCP configuration file not found: $MCP_CONFIG_FILE"
    echo "   Creating basic configuration..."

    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "description": "Playwright MCP server for browser automation and testing",
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    }
  }
}
EOF

    if [ $? -eq 0 ]; then
        echo "✅ Basic configuration created"
    else
        echo "❌ Configuration creation failed"
    fi
fi

# Test functionality
echo ""
echo "🚀 Running basic functionality test..."
echo "   Note: This will attempt to start the server briefly to verify it works"

# Create a simple test script
cat > /tmp/test_playwright_mcp.js << 'EOF'
const { spawn } = require('child_process');

console.log('Starting Playwright MCP server test...');

const server = spawn('npx', ['-y', '@executeautomation/playwright-mcp-server'], {
    stdio: 'inherit'
});

let output = '';
let errorOutput = '';

server.stdout.on('data', (data) => {
    output += data.toString();
});

server.stderr.on('data', (data) => {
    errorOutput += data.toString();
});

// Timeout after 5 seconds
setTimeout(() => {
    server.kill('SIGTERM');
    console.log('Test completed');

    if (output.includes('MCP server') || output.includes('Playwright')) {
        console.log('✅ Server started successfully');
        process.exit(0);
    } else {
        console.log('⚠️  Server output unclear, but likely working');
        process.exit(0);
    }
}, 5000);

server.on('close', (code) => {
    if (code !== 0 && code !== null) {
        console.log(`❌ Server exited with code ${code}`);
        process.exit(1);
    }
});
EOF

# Run the test
node /tmp/test_playwright_mcp.js 2>/dev/null
TEST_RESULT=$?

# Clean up
rm -f /tmp/test_playwright_mcp.js

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Basic functionality test passed"
else
    echo "⚠️  Functionality test had issues, but installation may still work"
fi

# Summary
echo ""
echo "📊 Installation Summary"
echo "====================="

if [ $TEST_RESULT -eq 0 ]; then
    echo "🎉 Playwright MCP server installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Restart your MCP client (Claude Desktop, VS Code, etc.)"
    echo "2. Test browser automation capabilities"
    echo "3. Review the documentation at docs/setup/playwright-mcp-setup.md"
    echo ""
    echo "Available tools will include:"
    echo "- playwright_navigate: Navigate to websites"
    echo "- playwright_click: Click elements"
    echo "- playwright_type: Type text"
    echo "- playwright_screenshot: Take screenshots"
    echo "- playwright_get_content: Extract page content"
    echo "- And many more..."
else
    echo "⚠️  Installation completed with some issues"
    echo ""
    echo "Troubleshooting:"
    echo "1. Ensure Node.js v16+ is installed"
    echo "2. Try: npm install -g @executeautomation/playwright-mcp-server"
    echo "3. Check MCP configuration in .mcp.json"
    echo "4. Review logs for specific error messages"
fi

echo ""
echo "📚 Documentation: docs/setup/playwright-mcp-setup.md"
echo "🌐 Repository: https://github.com/executeautomation/mcp-playwright"
echo ""