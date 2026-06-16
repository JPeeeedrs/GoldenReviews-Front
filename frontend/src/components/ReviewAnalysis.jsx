import GameHero from "./GameHero";
import AiSummaryBox from "./AiSummaryBox";
import StatGrid from "./StatGrid";
import TopicsGrid from "./TopicsGrid";

import "../styles/analysis.css";

export default function ReviewAnalysis({ data }) {
	if (!data) return null;

	const game = data.game || {};
	const summary = data.summary || {};
	const metadata = data.metadata || {};
	const meta = data.meta || {};

	const aiSummary = summary?.ai_text_summary;
	const aiSummaryText =
		typeof aiSummary === "object" ? aiSummary?.resumo : aiSummary;
	const aiNota = typeof aiSummary === "object" ? aiSummary?.nota_ia : null;

	return (
		<>
			{game?.header_image && (
				<div
					className='dynamic-bg'
					style={{ backgroundImage: `url(${game.header_image})` }}
				/>
			)}
			<section className='analysis'>
				<GameHero game={game} summary={summary} meta={meta} aiNota={aiNota} />
				<AiSummaryBox
					aiSummaryText={aiSummaryText}
					positivePct={summary?.positive_percentage || 0}
					negativePct={summary?.negative_percentage || 0}
				/>
				<StatGrid
					game={game}
					summary={summary}
					metadata={metadata}
					meta={meta}
				/>
				<TopicsGrid topics={data.topics} />
			</section>
		</>
	);
}
