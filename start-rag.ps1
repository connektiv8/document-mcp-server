# Quick Start Script for RAG System

Write-Host "🚀 Starting RAG Document Chat System..." -ForegroundColor Cyan

# Check if Docker is running
Write-Host "`n📦 Checking Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Stop any existing services
Write-Host "`n🛑 Stopping existing services..." -ForegroundColor Yellow
docker-compose -f docker-compose.rag.yml down 2>$null

# Build and start services
Write-Host "`n🔨 Building services (this may take a few minutes)..." -ForegroundColor Yellow
docker-compose -f docker-compose.rag.yml build

Write-Host "`n🚀 Starting all services..." -ForegroundColor Yellow
docker-compose -f docker-compose.rag.yml up -d

# Wait for services to be ready
Write-Host "`n⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check Ollama
Write-Host "`n🤖 Checking Ollama..." -ForegroundColor Yellow
$ollamaCheck = docker exec ollama ollama list 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Ollama is running" -ForegroundColor Green
    Write-Host "`nInstalled models:"
    docker exec ollama ollama list
} else {
    Write-Host "⚠️  Ollama is starting..." -ForegroundColor Yellow
}

# Suggest downloading a model
Write-Host "`n📥 Recommended: Download a model if you haven't already" -ForegroundColor Cyan
Write-Host "   Run: docker exec -it ollama ollama pull llama3.2:3b" -ForegroundColor White

# Check document indexing
Write-Host "`n📚 Checking document index..." -ForegroundColor Yellow
$docCount = Get-ChildItem -Path "data\documents" -File | Measure-Object | Select-Object -ExpandProperty Count
Write-Host "   Found $docCount document(s) in data/documents/" -ForegroundColor White

if ($docCount -gt 0) {
    Write-Host "`n💡 To index documents, run: python test_few_docs.py" -ForegroundColor Cyan
}

# Show service status
Write-Host "`n📊 Service Status:" -ForegroundColor Yellow
docker-compose -f docker-compose.rag.yml ps

# Final instructions
Write-Host "`n✨ RAG System is ready!" -ForegroundColor Green
Write-Host "`n🌐 Open your browser to: http://localhost:3000" -ForegroundColor Cyan
Write-Host "`n📖 View logs: docker-compose -f docker-compose.rag.yml logs -f" -ForegroundColor White
Write-Host "🛑 Stop system: docker-compose -f docker-compose.rag.yml down" -ForegroundColor White
Write-Host ""
