import "../styles/aisummarybox.css";

export default function AiSummaryBox({
	aiSummaryText,
	positivePct,
	negativePct,
}) {
	if (!aiSummaryText) return null;

	return (
		<div className='ai-summary-box'>
			<div className='ai-summary-header'>
				<h3>✨ Opinião dos Jogadores (Resumo IA)</h3>

				{(positivePct > 0 || negativePct > 0) && (
					<div
						className='sentiment-bar-wrapper'
						title={`${positivePct}% Positivas / ${negativePct}% Negativas`}
					>
						<div className='sentiment-bar'>
							<div className='bar-green' style={{ width: `${positivePct}%` }}>
								{positivePct > 10 && <span>{positivePct}%</span>}
							</div>
							<div className='bar-red' style={{ width: `${negativePct}%` }}>
								{negativePct > 10 && <span>{negativePct}%</span>}
							</div>
						</div>
					</div>
				)}
			</div>
			<p>{aiSummaryText}</p>
		</div>
	);
}
