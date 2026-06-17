import "../styles/aisummarybox.css";

export default function AiSummaryBox({
	aiSummaryText,
	aiNota, // Recebendo a nota em vez das porcentagens
}) {
	if (!aiSummaryText) return null;

	return (
		<div className='ai-summary-box'>
			<div
				className='ai-summary-header'
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<h3>✨ Opinião dos Jogadores (Resumo IA)</h3>

				{/* Exibindo a nota da IA se ela existir */}
				{aiNota !== undefined && aiNota !== null && aiNota > 0 && (
					<div
						className='ai-score-badge'
						style={{
							backgroundColor: "#171a21",
							padding: "6px 14px",
							borderRadius: "8px",
							border: "1px solid #66c0f4",
							color: "#66c0f4",
							fontWeight: "bold",
						}}
					>
						Nota IA: {aiNota}
					</div>
				)}
			</div>
			<p>{aiSummaryText}</p>
		</div>
	);
}
