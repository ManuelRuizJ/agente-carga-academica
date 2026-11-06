#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Servidor de Ollama SOLO CPU para laptops sin tarjeta gráfica dedicada.
#
# Por qué: tu Ryzen 7 5700U tiene una Radeon integrada (gfx90c) que ROCm no
# soporta. Ollama intentaba usarla y moría con
#   "ROCm error: invalid device function"
# Ese tipo de fallo del driver puede congelar o reiniciar la máquina.
#
# Este script:
#   * oculta TODAS las GPUs a Ollama (ROCm, CUDA, Vulkan) → nunca toca el driver
#   * usa tus modelos ya descargados en ~/.ollama/models (no descarga nada)
#   * escucha en el puerto 11435 (no choca con el servicio del sistema en 11434)
#   * 1 modelo a la vez, 1 petición a la vez, se descarga de RAM a los 2 min
#   * corre con prioridad baja (nice) para que el escritorio siga fluido
#
# Uso:   ./iniciar_ollama_cpu.sh            (déjalo abierto en otra terminal)
#        Ctrl+C para detenerlo y liberar toda la memoria.
# ---------------------------------------------------------------------------
set -euo pipefail

export OLLAMA_HOST="127.0.0.1:11435"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"

# Sin GPU
export HIP_VISIBLE_DEVICES=-1
export ROCR_VISIBLE_DEVICES=-1
export CUDA_VISIBLE_DEVICES=-1
export GGML_VK_VISIBLE_DEVICES=-1
export OLLAMA_VULKAN=0
export OLLAMA_LLM_LIBRARY=cpu

# Uso de memoria contenido
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=2m
export OLLAMA_CONTEXT_LENGTH=4096

if curl -s "http://$OLLAMA_HOST/api/version" >/dev/null 2>&1; then
  echo "Ya hay un Ollama escuchando en $OLLAMA_HOST"; exit 0
fi

echo "Ollama (solo CPU) en http://$OLLAMA_HOST  · modelos: $OLLAMA_MODELS"
echo "Ctrl+C para detenerlo."
exec nice -n 10 ollama serve
