from flask import Flask, render_template, jsonify, request, url_for, redirect
import psycopg2  # pip install psycopg2
import psycopg2.extras
from flask_restful import Resource, Api
from cachetools import Cache
import cachetools

DB_HOST = "database-2.cdcogkfzajf0.us-east-1.rds.amazonaws.com"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "15512332"

app = Flask(__name__)
api = Api(app)

def buscar_matriculas():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()

    cur.execute("select concat(matricula, ' - ', nome) as nome_matricula from requisicao.funcionarios")
    matriculas = cur.fetchall()
    matriculas_ = [item[0] for item in matriculas]

    return matriculas_

class SugestoesFuncionarios(Resource):
    def get(self):
        
        matriculas = buscar_matriculas()
        
        termo_busca = request.args.get('q', '').strip()  # Obtém o termo de busca da requisição

        print(termo_busca)

        # Se o termo de busca estiver vazio, retorna uma lista vazia
        if termo_busca == '':
            return jsonify({'results': []})

        sugestoes = [{'id': i, 'text': funcionario} for i, funcionario in enumerate(matriculas) if termo_busca.lower() in funcionario.lower()]

        return jsonify({'results': sugestoes})

api.add_resource(SugestoesFuncionarios, '/sugestoes_funcionarios')

def dados_tabela_requisicao():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # tabela de requisição 
    cur.execute(f"SELECT *, data_requisicao - interval '3 hours' AS nova_data FROM requisicao.requisicoes where motivo_exclusao isnull;")
    requisicoes = cur.fetchall()
    
    conn.commit()

    cur.close()
    conn.close()

    return requisicoes

def dados_tabela_transferencia():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # tabela de requisição 
    cur.execute(f"SELECT * FROM transferencia.transferencias;")
    transferencias = cur.fetchall()

    conn.commit()

    cur.close()
    conn.close()

    return transferencias

def query_exclusao_requisicao(chave, motivo):
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    sql_update = "update requisicao.requisicoes set motivo_exclusao = %s where id = %s"

    cur.execute(sql_update, (motivo,chave))

    conn.commit()

    cur.close()
    conn.close()

def query_autorizar_requisicao(chave):

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                        password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    sql_update = "update requisicao.requisicoes set status_almoxarifado = 'true' where id = %s"

    cur.execute(sql_update, (chave,))

    conn.commit()

    cur.close()
    conn.close()

@app.route('/inicio', methods=['GET'])
def inicio():

    # tabela de requisição 
    requisicoes = dados_tabela_requisicao()

    # tabela de transferência 
    transferencias = dados_tabela_transferencia()

    return render_template('inicio.html', requisicoes=requisicoes, transferencias=transferencias)

@app.route('/', methods=['GET'])
def index():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Requisição

    cur.execute("select concat(matricula, ' - ', nome) as nome_matricula from requisicao.funcionarios")
    matriculas = cur.fetchall()

    cur.execute("select distinct concat(codigo_ccusto, ' - ', ccusto) from requisicao.base_requisicoes_2023")
    ccustos = cur.fetchall()

    cur.execute("select distinct concat(t1.codigo, ' - ', t2.descricao) as codigo_descricao, unidade from requisicao.base_requisicoes_2023 as t1 left join requisicao.unidades as t2 on t1.codigo = t2.codigo")
    itens = cur.fetchall()

    # Transferência

    cur.execute("select distinct concat(codigo, ' - ', descricao) from transferencia.transferencias_2023")
    recursos_transferencia = cur.fetchall()

    cur.execute("select distinct deposito_destino from transferencia.transferencias_2023")
    deposito_destino = cur.fetchall()

    return render_template('index.html', matriculas=matriculas, ccustos=ccustos, itens=itens,
                            recursos_transferencia=recursos_transferencia, deposito_destino=deposito_destino)

# Rota para obter itens com base no centro de custo escolhido
@app.route('/itens_por_ccusto', methods=['GET'])
def itens_por_ccusto():
    ccusto = request.args.get('ccusto')

    ccusto = ccusto.split()[0]

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT distinct concat(codigo, ' - ', descricao) FROM requisicao.base_requisicoes_2023 WHERE codigo_ccusto = %s", (ccusto,))
    itens = cur.fetchall()

    return jsonify(itens)

# Rota para obter itens com base no item escolhido
@app.route('/classe_por_item', methods=['GET'])
def classe_por_item():
    item = request.args.get('item')

    item = item.split()[0]

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT distinct classe_requisicao FROM requisicao.base_requisicoes_2023 WHERE codigo = %s", (item,))
    itens = cur.fetchall()

    return jsonify(itens)

# Rota para obter unidade com base no item escolhido
@app.route('/unidade_por_item', methods=['GET'])
def unidade_por_item():
    item = request.args.get('item')

    item = item.split()[0]

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("select distinct unidade from requisicao.unidades where codigo = %s", (item,))

    try:
        unidade = cur.fetchall()[0]
    except:
        unidade = 'Não encontrada'

    return jsonify(unidade)

@app.route('/salvar-requisicao', methods=['POST'])
def salvar_requisicao():
    
    funcionario = request.form.get('inputFuncionario')
    item = request.form.get('inputItem')
    ccusto = request.form.get('inputCcusto')
    classe = request.form.get('inputClasse')
    quantidade = request.form.get('inputQuantidade')
    observacao = request.form.get('textAreaObservacao')

    values = [funcionario,ccusto,item,quantidade,classe,observacao]

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    
    cur.execute("INSERT INTO requisicao.requisicoes (funcionario, ccusto, item, quantidade, classe, observacao) VALUES (%s, %s, %s, %s, %s, %s)", tuple(values))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("index"))

@app.route('/salvar-transferencia', methods=['POST'])
def salvar_transferencia():
    
    funcionario = request.form.get('inputFuncionario')
    item = request.form.get('inputItem')
    deposito = request.form.get('inputDeposito')
    quantidade = request.form.get('inputQuantidade')

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    
    cur.execute("INSERT INTO transferencia.transferencias (funcionario,deposito_origem,recurso,quantidade) VALUES (%s,%s,%s,%s)", (funcionario,deposito,item,quantidade))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("index"))

@app.route('/api/publica/requisicoes', methods=['GET'])
def registros_requisicoes():
    try:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM requisicao.requisicoes ORDER BY id;")
        requisicoes = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(requisicoes)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/publica/transferencias', methods=['GET'])
def registros_transferencias():
    try:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM transferencia.transferencias ORDER BY id;")
        transferencia = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(transferencia)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teste/publica/requisicoes', methods=['GET'])
def registros_requisicoes_teste():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(f"SELECT * FROM requisicao.requisicoes;")
    requisicoes = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({'data': requisicoes,})

@app.route('/salvar-edicao-tabela-requisicao', methods=['POST'])
def salvar_edicao_tabela_requisicao():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    chave = request.form.get('chave')
    item = request.form.get('item')
    quantidade = request.form.get('quantidade')

    print(chave,item,quantidade)

    sql_query_edit = "update requisicao.requisicoes set item = %s, quantidade = %s where id = %s"
    cur.execute(sql_query_edit, (item,quantidade,chave,))

    conn.commit()

    sql_consulta = "select * from requisicao.requisicoes"
    cur.execute(sql_consulta)
    data = cur.fetchall()

    cur.close()
    conn.close()

    print(data)

    return jsonify(data)

@app.route('/autorizar-requisicao', methods=['POST'])
def autorizar_requisicao():

    chave = request.form.get('chave')

    query_autorizar_requisicao(chave)
    
    data = dados_tabela_requisicao()

    return jsonify(data)

@app.route('/exclusao-requisicao', methods=['POST'])
def exclusao_requisicao():

    chave = request.form.get('chave')
    motivo = request.form.get('motivo')

    query_exclusao_requisicao(chave,motivo)

    data = dados_tabela_requisicao()

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)