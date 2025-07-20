#!/bin/bash

# HHAI Pair Programming Frontend - Vercel Deployment Script
# Make sure to run this script from the frontend directory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL=""
PROJECT_NAME="hhai-pair-programming-frontend"

echo -e "${BLUE}🚀 Starting HHAI Pair Programming Frontend Deployment${NC}"

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "vite.config.ts" ]; then
    echo -e "${RED}❌ Please run this script from the frontend directory${NC}"
    exit 1
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}⚠️  Vercel CLI not found. Installing...${NC}"
    npm install -g vercel
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    npm install
fi

# Get backend URL if not provided
if [ -z "$BACKEND_URL" ]; then
    echo -e "${YELLOW}📝 Please provide your backend URL (e.g., https://your-service-name.run.app):${NC}"
    read -r BACKEND_URL
fi

# Validate backend URL
if [[ ! $BACKEND_URL =~ ^https?:// ]]; then
    echo -e "${RED}❌ Invalid backend URL. Please include http:// or https://❌"
    exit 1
fi

echo -e "${BLUE}🔧 Updating Vercel configuration with backend URL...${NC}"

# Update vercel.json with the new backend URL
cat > vercel.json << EOF
{
    "rewrites": [
        {"source": "/api/:path*", "destination": "${BACKEND_URL}/:path*"},
        {"source": "/(.*)", "destination": "/"}
    ],
    "headers": [
        {
            "source": "/api/(.*)",
            "headers": [
                {
                    "key": "Access-Control-Allow-Origin",
                    "value": "*"
                },
                {
                    "key": "Access-Control-Allow-Methods",
                    "value": "GET, POST, PUT, DELETE, OPTIONS"
                },
                {
                    "key": "Access-Control-Allow-Headers",
                    "value": "Content-Type, Authorization"
                }
            ]
        }
    ]
}
EOF

echo -e "${GREEN}✅ Vercel configuration updated${NC}"

echo -e "${BLUE}🏗️  Building the project...${NC}"
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build successful${NC}"

echo -e "${BLUE}🚀 Deploying to Vercel...${NC}"

# Deploy to Vercel
vercel --prod

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Vercel deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Frontend deployed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test your deployment by visiting the Vercel URL"
echo "2. Check the browser console for any errors"
echo "3. Verify API calls are working properly"
echo ""
echo -e "${BLUE}🔗 Useful commands:${NC}"
echo "View deployments: vercel ls"
echo "View logs: vercel logs"
echo "Redeploy: vercel --prod"
