import streamlit as st
import pandas as pd
import io
from collections import Counter

# Configuração da página
st.set_page_config(page_title="Otimizador de Cortes PRO", page_icon="🪚", layout="centered")

st.title("🪚 Otimizador de Plano de Corte PRO")
st.markdown("Cálculo industrial: Considera a espessura da lâmina e o espaço da morsa/pinça.")
st.markdown("**Planilha (5 colunas):** Tamanho da Barra | Peça | Quantidade | Serra | Espaço da Pinça")

# Botão de upload
arquivo_upload = st.file_uploader("Arraste sua planilha Excel aqui (.xlsx)", type=["xlsx"])

if arquivo_upload is not None:
    try:
        # Lê a planilha enviada
        df_entrada = pd.read_excel(arquivo_upload)
        
        # Lendo os novos parâmetros físicos da primeira linha
        tamanho_barra = float(df_entrada.iloc[0, 0])
        espessura_serra = float(df_entrada.iloc[0, 3]) # Coluna D
        espaco_pinca = float(df_entrada.iloc[0, 4])    # Coluna E
        
        # MATEMÁTICA DO MUNDO REAL: A área da barra que realmente pode ser cortada
        tamanho_util_barra = tamanho_barra - espaco_pinca
        
        # Lê as peças (Colunas B e C)
        pecas_originais = []
        df_pecas = df_entrada.iloc[:, [1, 2]].dropna()
        
        for index, row in df_pecas.iterrows():
            tamanho = float(row.iloc[0])
            quantidade = int(row.iloc[1])
            pecas_originais.extend([tamanho] * quantidade)
        
        st.info(f"**Setup da Máquina:** Barra de {tamanho_barra} | Lâmina consome {espessura_serra} por corte | Morsa exige {espaco_pinca} livres.")
        st.warning(f"**Área Útil de Corte por barra:** {tamanho_util_barra}")
        
        with st.spinner("Calculando o melhor encaixe físico..."):
            pecas_normais = []
            pecas_gigantes = []

            # Verifica quais peças cabem usando a matemática nova
            for p in pecas_originais:
                # Cada peça "rouba" o seu próprio tamanho + a espessura da serra para soltá-la
                tamanho_fisico_real = p + espessura_serra
                
                if tamanho_fisico_real > tamanho_util_barra:
                    pecas_gigantes.append({'original': p, 'com_serra': tamanho_fisico_real})
                else:
                    pecas_normais.append({'original': p, 'com_serra': tamanho_fisico_real})

            # Organiza da maior para a menor
            pecas_normais.sort(key=lambda x: x['com_serra'], reverse=True)
            barras = []
            sobras_uteis = []

            # Algoritmo de encaixe
            for peca in pecas_normais:
                encaixou = False
                for i in range(len(barras)):
                    # A sobra útil que sobrou nessa barra aguenta o tamanho da peça + a serra?
                    if sobras_uteis[i] >= peca['com_serra']:
                        barras[i].append(peca['original'])
                        sobras_uteis[i] -= peca['com_serra']
                        encaixou = True
                        break
                
                # Se não encaixou, puxa uma barra nova do estoque
                if not encaixou:
                    barras.append([peca['original']])
                    sobras_uteis.append(tamanho_util_barra - peca['com_serra'])

            # Prepara a tabela de resultado agrupada
            dados_saida = []
            for i in range(len(barras)):
                contagem = Counter(barras[i])
                textos_agrupados = [f"{qtd}x {peca}" if qtd > 1 else str(peca) for peca, qtd in contagem.items()]
                texto_final = " + ".join(textos_agrupados)

                # A sobra física final é o que sobrou da área útil + o pedaço que estava preso na morsa
                sobra_real_fisica = sobras_uteis[i] + espaco_pinca
                # Quantidade de material que virou pó com os cortes
                material_perdido_em_po = len(barras[i]) * espessura_serra

                dados_saida.append({
                    "Barra": f"Barra {i + 1}",
                    "Esquema de Corte": texto_final,
                    "Retalho Final / Sobra": round(sobra_real_fisica, 2),
                    "Material em Pó (Serragem)": round(material_perdido_em_po, 2)
                })

            # Avalia peças que a máquina não consegue cortar
            if pecas_gigantes:
                contagem_gigantes = Counter([p['original'] for p in pecas_gigantes])
                for peca, qtd in contagem_gigantes.items():
                    texto_gigante = f"{qtd}x {peca}" if qtd > 1 else str(peca)
                    falta = (peca + espessura_serra) - tamanho_util_barra
                    
                    dados_saida.append({
                        "Barra": "⚠ Não cabe na Máquina",
                        "Esquema de Corte": texto_gigante,
                        "Retalho Final / Sobra": f"Falta {round(falta, 2)} de espaço útil na barra",
                        "Material em Pó (Serragem)": "-"
                    })

            df_saida = pd.DataFrame(dados_saida)

            st.success("✅ Simulação física concluída com sucesso!")
            
            # Mostra o resumo na tela
            col1, col2 = st.columns(2)
            col1.metric("Barras Padrão Necessárias", len(barras))
            col2.metric("Peças Inválidas (Não cabem)", len(pecas_gigantes))

            st.write("### Pré-visualização do Relatório:")
            st.dataframe(df_saida, use_container_width=True)

            # Prepara o arquivo Excel para baixar
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_saida.to_excel(writer, index=False, sheet_name='Plano Físico')
            
            dados_excel = output.getvalue()

            st.download_button(
                label="📥 Baixar Plano de Corte Físico",
                data=dados_excel,
                file_name="plano_de_corte_fisico_pro.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Erro ao processar a planilha. Verifique se ela possui as 5 colunas corretamente. Detalhe: {e}")