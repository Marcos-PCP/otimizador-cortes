import streamlit as st
import pandas as pd
import io
from collections import Counter

# Configuração da página
st.set_page_config(page_title="Otimizador de Cortes", page_icon="🪚", layout="centered")

st.title("🪚 Otimizador de Plano de Corte")
st.markdown("Faça o upload da sua planilha para calcular a melhor forma de cortar suas barras comerciais.")
st.markdown("**Formato esperado (4 colunas):** Tamanho da Barra | Tamanho da Peça | Quantidade | Indice de Perda")

# Botão de upload
arquivo_upload = st.file_uploader("Arraste sua planilha Excel aqui (.xlsx)", type=["xlsx"])

if arquivo_upload is not None:
    try:
        # Lê a planilha
        df_entrada = pd.read_excel(arquivo_upload)
        
        # Pega os parâmetros gerais (Coluna A e Coluna D)
        tamanho_barra = float(df_entrada.iloc[0, 0])
        perda = float(df_entrada.iloc[0, 3]) # Agora a perda está na 4ª coluna (índice 3)
        
        # Lê as peças e quantidades (Colunas B e C)
        pecas_originais = []
        # Pega apenas as linhas que têm tamanho e quantidade preenchidos
        df_pecas = df_entrada.iloc[:, [1, 2]].dropna()
        
        for index, row in df_pecas.iterrows():
            tamanho = float(row.iloc[0])
            quantidade = int(row.iloc[1])
            # Multiplica a peça pela quantidade e adiciona na lista
            pecas_originais.extend([tamanho] * quantidade)
        
        st.info(f"**Parâmetros:** Barra de {tamanho_barra} | Perda de {perda*100}% | Total de {len(pecas_originais)} peças individuais para cortar.")
        
        with st.spinner("Calculando o melhor encaixe..."):
            pecas_normais = []
            pecas_gigantes = []

            # Verifica quais peças cabem
            for p in pecas_originais:
                tamanho_real = p * (1 + perda)
                if tamanho_real > tamanho_barra:
                    pecas_gigantes.append({'original': p, 'com_perda': tamanho_real})
                else:
                    pecas_normais.append({'original': p, 'com_perda': tamanho_real})

            # Organiza da maior para a menor
            pecas_normais.sort(key=lambda x: x['com_perda'], reverse=True)
            barras = []
            sobras = []

            # Algoritmo de encaixe (Serralheiro Inteligente)
            for peca in pecas_normais:
                encaixou = False
                for i in range(len(barras)):
                    if sobras[i] >= peca['com_perda']:
                        barras[i].append(peca['original'])
                        sobras[i] -= peca['com_perda']
                        encaixou = True
                        break
                
                if not encaixou:
                    barras.append([peca['original']])
                    sobras.append(tamanho_barra - peca['com_perda'])

            # Prepara a tabela de resultado com AGRUPAMENTO INTELIGENTE
            dados_saida = []
            for i in range(len(barras)):
                # Agrupa peças iguais (Ex: converte [43, 43, 43] para "3x 43")
                contagem = Counter(barras[i])
                textos_agrupados = []
                for peca, qtd in contagem.items():
                    if qtd > 1:
                        textos_agrupados.append(f"{qtd}x {peca}")
                    else:
                        textos_agrupados.append(str(peca))
                        
                texto_final = " + ".join(textos_agrupados)

                dados_saida.append({
                    "Barra": f"Barra {i + 1}",
                    "Peças Cortadas": texto_final,
                    "Sobra Guardada": round(sobras[i], 2)
                })

            # Adiciona as gigantes
            if pecas_gigantes:
                contagem_gigantes = Counter([p['original'] for p in pecas_gigantes])
                for peca, qtd in contagem_gigantes.items():
                    # Calcula o quanto passou baseado em UMA peça (já que todas são iguais)
                    tamanho_com_perda = peca * (1 + perda)
                    falta = tamanho_com_perda - tamanho_barra
                    texto_gigante = f"{qtd}x {peca}" if qtd > 1 else str(peca)
                    
                    dados_saida.append({
                        "Barra": "⚠ Necessita Barra Maior",
                        "Peças Cortadas": texto_gigante,
                        "Sobra Guardada": f"Cada peça passa {round(falta, 2)} do limite"
                    })

            df_saida = pd.DataFrame(dados_saida)

            st.success("✅ Cálculo concluído com sucesso!")
            
            # Mostra o resumo na tela
            col1, col2 = st.columns(2)
            col1.metric("Barras Padrão Necessárias", len(barras))
            col2.metric("Peças Gigantes (Não couberam)", len(pecas_gigantes))

            st.write("### Pré-visualização do Relatório:")
            st.dataframe(df_saida, use_container_width=True)

            # Prepara o arquivo Excel para baixar
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_saida.to_excel(writer, index=False, sheet_name='Plano de Corte')
            
            dados_excel = output.getvalue()

            # Botão de Download
            st.download_button(
                label="📥 Baixar Planilha de Resultados",
                data=dados_excel,
                file_name="plano_de_corte_otimizado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Erro ao processar a planilha. Verifique se ela possui as 4 colunas corretamente. Detalhe do erro: {e}")