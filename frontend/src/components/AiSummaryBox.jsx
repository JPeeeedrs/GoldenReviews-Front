import "../styles/aisummarybox.css";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

export default function AiSummaryBox({ aiSummaryText, aiNota }) {
	if (!aiSummaryText) return null;

	return (
		<div className='ai-summary-box'>
			<div className='ai-summary-header'>
				<h3>✨ Opinião dos Jogadores (Resumo IA)</h3>
				{aiNota !== null && <span>⭐ {numberFormat(aiNota)} / 5.0</span>}
			</div>
			<p>{aiSummaryText}</p>
		</div>
	);
}
