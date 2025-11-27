# Sistema de Movimentos Fiscais - Nova Estrutura

## 📋 Visão Geral

Este sistema foi reestruturado para usar um banco de dados **normalizado** ao invés de armazenar dados complexos em campos JSON. Agora você tem acesso direto e fácil a todos os dados através de relacionamentos.

## 🎯 Principais Mudanças

### ❌ Antes (Estrutura Antiga)
```python
# Dados em JSON - difícil de acessar
movement.get_json_field('cost_center_apportionments')
```

### ✅ Agora (Estrutura Nova)
```python
# Dados normalizados - acesso direto
movement.cost_center_apportionments
apportionment.cost_center.name  # Nome disponível diretamente!
```

## 🗄️ Estrutura do Banco

```
Company (Empresas)
├── Branch (Filiais)
├── CostCenter (Centros de Custo)
├── Product (Produtos)
├── CustomerVendor (Clientes/Fornecedores)
└── FinancialMovement (Movimentos)
    ├── MovementItem (Itens)
    │   ├── → Product
    │   └── → CostCenter
    ├── MovementPayment (Pagamentos)
    ├── MovementTax (Impostos)
    └── CostCenterApportionment (Rateios)
        └── → CostCenter
```

## 🚀 Como Usar

### 1. Testar o Sistema

Execute os testes para verificar se tudo está funcionando:

```bash
python test_new_system.py
```

Este script irá:
- ✅ Criar as tabelas no banco
- ✅ Testar o cache de entidades
- ✅ Testar a conexão com a API TOTVS

### 2. Importar Dados da API

Use o comando abaixo para importar movimentos diretamente da API:

```bash
python api_importer.py --inicio 2025-08-01 --fim 2025-11-01 --empresa 4 --filial 17
```

**Parâmetros:**
- `--inicio`: Data inicial (YYYY-MM-DD)
- `--fim`: Data final (YYYY-MM-DD)
- `--empresa`: Código da empresa
- `--filial`: Código da filial
- `--page-size`: (Opcional) Itens por página (padrão: 50)
- `--max-pages`: (Opcional) Máximo de páginas (padrão: 1000)

**Exemplo com mais opções:**
```bash
python api_importer.py \
  --inicio 2025-08-01 \
  --fim 2025-11-01 \
  --empresa 4 \
  --filial 17 \
  --page-size 100 \
  --max-pages 500
```

### 3. Acessar Dados no Template

Com a nova estrutura, acessar dados ficou muito mais simples:

#### Dados da Empresa e Filial
```jinja2
<h1>{{ movement.company.name }}</h1>
<h2>{{ movement.branch.name }}</h2>
```

#### Cliente/Fornecedor
```jinja2
<p>Cliente: {{ movement.customer_vendor.name }}</p>
<p>CNPJ: {{ movement.customer_vendor.cnpj }}</p>
```

#### Rateios de Centro de Custo
```jinja2
{% for apportionment in movement.cost_center_apportionments %}
  <tr>
    <td>{{ apportionment.cost_center.code }}</td>
    <td>{{ apportionment.cost_center.name }}</td>
    <td>R$ {{ "%.2f"|format(apportionment.value) }}</td>
  </tr>
{% endfor %}
```

#### Itens do Movimento
```jinja2
{% for item in movement.items %}
  <tr>
    <td>{{ item.product.name }}</td>
    <td>{{ item.cost_center.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>R$ {{ "%.2f"|format(item.unit_price) }}</td>
    <td>R$ {{ "%.2f"|format(item.total_value) }}</td>
  </tr>
{% endfor %}
```

#### Pagamentos
```jinja2
{% for payment in movement.payments %}
  <tr>
    <td>{{ payment.due_date.strftime('%d/%m/%Y') if payment.due_date else '-' }}</td>
    <td>R$ {{ "%.2f"|format(payment.value) }}</td>
  </tr>
{% endfor %}
```

## 📊 Consultas no Python

### Buscar Movimentos por Centro de Custo
```python
from models_new import FinancialMovement, CostCenter, CostCenterApportionment

movements = FinancialMovement.query.join(
    CostCenterApportionment
).join(
    CostCenter
).filter(
    CostCenter.name.like('%Marketing%')
).all()
```

### Total por Centro de Custo
```python
from sqlalchemy import func

totals = db.session.query(
    CostCenter.name,
    func.sum(CostCenterApportionment.value)
).join(
    CostCenterApportionment
).group_by(
    CostCenter.name
).all()

for cc_name, total in totals:
    print(f"{cc_name}: R$ {total:.2f}")
```

### Movimentos por Período
```python
from datetime import datetime

start_date = datetime(2025, 8, 1)
end_date = datetime(2025, 11, 1)

movements = FinancialMovement.query.filter(
    FinancialMovement.date >= start_date,
    FinancialMovement.date <= end_date
).order_by(
    FinancialMovement.date.desc()
).all()
```

## 🔧 Arquivos Principais

- **`models_new.py`**: Novos modelos normalizados
- **`api_importer.py`**: Importador da API TOTVS
- **`test_new_system.py`**: Testes do sistema
- **`README_NEW_SYSTEM.md`**: Este arquivo

## ⚠️ Importante

1. **Banco de Dados Limpo**: Como você confirmou que pode começar do zero, o banco será recriado com a nova estrutura.

2. **Performance**: O sistema está otimizado para milhares de registros com índices apropriados.

3. **Cache**: O importador usa cache para evitar duplicação de empresas, filiais, centros de custo, etc.

4. **Commits Parciais**: O importador faz commit a cada 10 movimentos para evitar transações muito grandes.

## 📝 Próximos Passos

1. ✅ Testar o sistema: `python test_new_system.py`
2. ✅ Importar dados: `python api_importer.py --inicio ... --fim ... --empresa ... --filial ...`
3. ⏳ Criar novo template `detail_new.html`
4. ⏳ Testar visualização dos dados
5. ⏳ Substituir templates antigos

## 🆘 Troubleshooting

### Erro de Conexão com a API
Verifique se o servidor TOTVS está acessível:
```bash
curl http://192.168.18.9:8051/api/mov/v1/movements?page=1&pageSize=1
```

### Erro ao Criar Tabelas
Certifique-se de que o banco de dados está configurado corretamente no `app.py`.

### Importação Lenta
- Reduza o `--page-size` se estiver tendo timeouts
- Aumente o `--page-size` se a rede estiver estável

## 📞 Suporte

Se encontrar problemas, verifique:
1. Logs do importador (são bem detalhados)
2. Status da API TOTVS
3. Configuração do banco de dados
