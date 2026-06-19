import streamlit as st
import pandas as pd
import io

# Configuração da página
st.set_page_config(page_title="Otimizador de Cortes", page_icon="🪚", layout="centered")

st.title("🪚 Otimizador de Plano de Corte")
st.markdown("Faça o upload da sua planilha para calcular a melhor forma de cortar suas barras comerciais.")

# Botão de upload
arquivo_upload = st.file_uploader("Arraste sua planilha Excel aqui (.xlsx)", type=["xlsx"])

if arquivo_upload is not None:
    try:
        # Lê a planilha
        df_entrada = pd.read_excel(arquivo_upload)
        tamanho_barra = float(df_entrada.iloc[0, 0])
        perda = float(df_entrada.iloc[0, 2])
        pecas_originais = df_entrada.iloc[:, 1].dropna().tolist()
        
        st.info(f"**Parâmetros identificados:** Barra de {tamanho_barra} | Perda de {perda*100}% | {len(pecas_originais)} peças para cortar.")
        
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

            # Algoritmo de encaixe
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

            # Prepara a tabela de resultado
            dados_saida = []
            for i in range(len(barras)):
                dados_saida.append({
                    "Barra": f"Barra {i + 1}",
                    "Peças Cortadas": " + ".join([str(p) for p in barras[i]]),
                    "Sobra Guardada": round(sobras[i], 2)
                })

            if pecas_gigantes:
                for peca in pecas_gigantes:
                    falta = peca['com_perda'] - tamanho_barra
                    dados_saida.append({
                        "Barra": "⚠ Necessita Barra Maior",
                        "Peças Cortadas": str(peca['original']),
                        "Sobra Guardada": f"Passou {round(falta, 2)} do limite"
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
        st.error(f"Erro ao processar a planilha. Verifique se o formato está igual ao modelo. Detalhe: {e}")