import sqlite3

print("=" * 80)
print("🔍 VERIFICANDO BANCOS DE DADOS")
print("=" * 80)

# Banco V1
print("\n📊 BANCO V1 (financial_data.db):")
try:
    conn1 = sqlite3.connect('instance/financial_data.db')
    cursor1 = conn1.cursor()
    
    # Conta movimentos
    cursor1.execute("SELECT COUNT(*) FROM financial_movement")
    count_v1 = cursor1.fetchone()[0]
    print(f"   Movimentos: {count_v1}")
    
    # Conta empresas
    cursor1.execute("SELECT COUNT(*) FROM company")
    companies_v1 = cursor1.fetchone()[0]
    print(f"   Empresas: {companies_v1}")
    
    # Conta filiais
    cursor1.execute("SELECT COUNT(*) FROM branch")
    branches_v1 = cursor1.fetchone()[0]
    print(f"   Filiais: {branches_v1}")
    
    conn1.close()
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Banco V2
print("\n📊 BANCO V2 (financial_data_v2.db):")
try:
    conn2 = sqlite3.connect('instance/financial_data_v2.db')
    cursor2 = conn2.cursor()
    
    # Conta movimentos
    cursor2.execute("SELECT COUNT(*) FROM financial_movement_v2")
    count_v2 = cursor2.fetchone()[0]
    print(f"   Movimentos: {count_v2}")
    
    # Conta empresas
    cursor2.execute("SELECT COUNT(*) FROM company_v2")
    companies_v2 = cursor2.fetchone()[0]
    print(f"   Empresas: {companies_v2}")
    
    # Conta filiais
    cursor2.execute("SELECT COUNT(*) FROM branch_v2")
    branches_v2 = cursor2.fetchone()[0]
    print(f"   Filiais: {branches_v2}")
    
    conn2.close()
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "=" * 80)
print("💡 CONCLUSÃO:")
print("=" * 80)

if count_v1 == 0 and count_v2 > 0:
    print("⚠️  O banco V1 está VAZIO, mas o V2 tem dados!")
    print("   Você está acessando /movements (V1) mas deveria acessar /movements_v2/")
    print("\n   SOLUÇÃO:")
    print("   1. Acesse http://seu-servidor/movements_v2/ para ver os dados")
    print("   2. OU migre os dados do V2 para o V1")
    print("   3. OU importe dados direto para o V1")
elif count_v1 > 0:
    print(f"✅ O banco V1 tem {count_v1} movimentos")
    print("   A rota /movements deveria estar funcionando")
else:
    print("⚠️  Ambos os bancos estão vazios!")
    print("   Você precisa importar dados primeiro")
