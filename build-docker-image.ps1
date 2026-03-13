# Build Docker Image with Payment Integration
# This script builds the Docker image that includes all payment code

Write-Host "🔨 Building Docker image with payment integration..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "📦 Building image: my-open-notebook:latest" -ForegroundColor Yellow
Write-Host "⏱️  This may take 5-10 minutes..." -ForegroundColor Gray
Write-Host ""

# Build the Docker image
docker build -t my-open-notebook:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Docker image built successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Start the containers: docker-compose up -d" -ForegroundColor White
    Write-Host "2. Check logs: docker-compose logs -f open_notebook" -ForegroundColor White
    Write-Host "3. Verify payment routes: http://localhost:5055/docs" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    exit 1
}
