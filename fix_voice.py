import re
with open("frontend/src/components/WorkerVoiceAssistant.jsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("const isHindi = true", "const isHindi = false")
with open("frontend/src/components/WorkerVoiceAssistant.jsx", "w", encoding="utf-8") as f:
    f.write(content)

