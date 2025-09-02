#!/bin/bash

echo "🧪 Testing BridgeWise API..."

# Test health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if [ $? -eq 0 ]; then
    echo "✅ Health endpoint: $HEALTH_RESPONSE"
else
    echo "❌ Health endpoint failed"
    exit 1
fi

# Test portfolio endpoint
echo "Testing portfolio endpoint..."
PORTFOLIO_RESPONSE=$(curl -s http://localhost:8000/api/portfolio)
if [ $? -eq 0 ]; then
    echo "✅ Portfolio endpoint: Response received"
    echo "   Items count: $(echo $PORTFOLIO_RESPONSE | jq '. | length' 2>/dev/null || echo 'Unknown')"
else
    echo "❌ Portfolio endpoint failed"
    exit 1
fi

# Test portfolio stats endpoint
echo "Testing portfolio stats endpoint..."
STATS_RESPONSE=$(curl -s http://localhost:8000/api/portfolio/stats)
if [ $? -eq 0 ]; then
    echo "✅ Portfolio stats endpoint: Response received"
else
    echo "❌ Portfolio stats endpoint failed"
    exit 1
fi

echo ""
echo "🎉 All API tests passed!"
echo "🔗 API Documentation: http://localhost:8000/docs"
