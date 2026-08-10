# Arquitetura

Camadas:

- `domain`: regras e contratos puros.
- `infrastructure`: OpenCV, banco e implementações técnicas.
- `api`: interface HTTP.
- `frontend`: visualização e controle do laboratório.

Regra: domínio não depende de infraestrutura.
