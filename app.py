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

cache_matriculas = cachetools.LRUCache(maxsize=128)

@cachetools.cached(cache_matriculas)
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

    cur.execute("select distinct concat(codigo, ' - ', descricao) from requisicao.base_requisicoes_2023")
    itens = cur.fetchall()

    # Tranferência

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

@app.route('/salvar-requisicao', methods=['POST'])
def salvar_requisicao():
    
    selectFuncionario = request.form.get('selectFuncionario')
    selectItem = request.form.get('selectItem')
    selectCcusto = request.form.get('selectCcusto')
    selectClasse = request.form.get('selectClasse')
    quantidade = request.form.get('quantidade')
    observacao = request.form.get('observacao')

    print(selectFuncionario,selectItem,selectCcusto,selectClasse,quantidade,observacao)

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    
    cur.execute("INSERT INTO requisicao.requisicoes (funcionario,ccusto,item,quantidade,classe,observacao) VALUES (%s,%s,%s,%s,%s,%s)", (selectFuncionario,selectCcusto,selectItem,quantidade,selectClasse,observacao))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("index"))

@app.route('/salvar-transferencia', methods=['POST'])
def salvar_transferencia():
    
    selectFuncionario = request.form.get('selectFuncionarioTransferencia')
    selectItem = request.form.get('selectItemTransferencia')
    selectDepositoDestino = request.form.get('selectDepositoDestino')
    quantidade = request.form.get('quantidade')

    print(selectFuncionario,selectItem,quantidade,selectDepositoDestino)

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                            password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    
    cur.execute("INSERT INTO transferencia.transferencias (funcionario,deposito_origem,recurso,quantidade) VALUES (%s,%s,%s,%s)", (selectFuncionario,selectDepositoDestino,selectItem,quantidade))

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

if __name__ == '__main__':
    app.run(debug=True)