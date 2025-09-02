# 🔧 GitHub API Rate Limits & Solutions

## 🚨 **Current Issue: Rate Limit Exceeded**

You're hitting GitHub's API rate limits because our analyzer makes multiple API calls per repository analysis.

## 📊 **API Usage Breakdown**

### **Endpoints Used Per Analysis**
1. **Repository Info** - `GET /repos/{owner}/{repo}` (1 call)
2. **File Structure** - `GET /repos/{owner}/{repo}/contents/{path}` (10-40 calls)
3. **Commit History** - `GET /repos/{owner}/{repo}/commits` (1 call)

**Total: ~12-42 API calls per repository**

### **Rate Limits**
- **Without Token**: 60 requests/hour (can analyze ~1-2 repos/hour)
- **With Token**: 5,000 requests/hour (can analyze ~100-200 repos/hour)

## 🚀 **Solutions**

### **Quick Fix: Get GitHub Personal Access Token**

1. **Create Token**:
   ```
   1. Go to: https://github.com/settings/tokens
   2. Click "Generate new token (classic)"
   3. Select scope: "public_repo" 
   4. Copy the token (starts with ghp_)
   ```

2. **Use Token in Frontend**:
   Update your Portfolio Builder to include the token:

   ```typescript
   // In PortfolioBuilderModal.tsx, modify the API call:
   const response = await fetch('http://localhost:8000/analyze', {
     method: 'POST',
     mode: 'cors',
     headers: {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
     },
     body: JSON.stringify({
       github_url: url,
       github_token: "ghp_your_token_here" // Add your token here
     })
   });
   ```

3. **Test with Token**:
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "github_url": "https://github.com/facebook/react",
       "github_token": "ghp_your_token_here"
     }'
   ```

### **Alternative: Optimize Without Token**

If you prefer not to use a token, I've optimized the API usage:

- **Reduced recursion depth** (2 levels instead of 3)
- **Limited file analysis** (15 files per directory instead of 20)
- **Prioritized important files** (README, package.json, etc.)
- **Better rate limit error messages**

### **Production Solution: Environment Variables**

For production, store the token securely:

1. **Create `.env` file**:
   ```bash
   echo "GITHUB_TOKEN=ghp_your_token_here" > github-analyzer-api/.env
   ```

2. **Update FastAPI to use environment variables**:
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   DEFAULT_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
   ```

## 🔍 **Check Current Rate Limit Status**

```bash
# Without token
curl -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/rate_limit

# With token  
curl -H "Accept: application/vnd.github.v3+json" \
     -H "Authorization: token ghp_your_token_here" \
     https://api.github.com/rate_limit
```

## ⚡ **Rate Limit Best Practices**

1. **Use Authentication** - Always use a token for 5,000/hour limit
2. **Cache Results** - Store analysis results to avoid re-analyzing
3. **Batch Requests** - Analyze multiple files in single requests when possible
4. **Monitor Headers** - Check `X-RateLimit-Remaining` in responses
5. **Handle Gracefully** - Provide meaningful error messages to users

## 🎯 **Recommended Next Steps**

1. **Immediate**: Get a GitHub token and add it to your requests
2. **Short-term**: Add token input field to Portfolio Builder UI
3. **Long-term**: Implement caching and request optimization

This will solve your rate limit issues and make the Portfolio Builder much more reliable!
