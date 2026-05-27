import { useMemo, useState } from "react";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

const integerFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);

export default function ReviewAnalysis({ data }) {
	const [topicView, setTopicView] = useState("positive");

	const orderedTopics = useMemo(() => {
		const items = data?.topics?.[topicView] ?? [];
		return [...items].sort((a, b) => (b?.mentions ?? 0) - (a?.mentions ?? 0));
	}, [data?.topics, topicView]);

	if (!data) return null;

	const { game, summary, highlights, metadata, meta } = data;
	const topicLabel = topicView === "positive" ? "Positivos" : "Negativos";

	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;
	const avgHours = summary?.avg_hours;

	return (
		<section className='analysis'>
			<header className='analysis-hero'>
				<div>
					<p className='eyebrow'>Golden Reviews • jogo em análise</p>
					<h2>{game?.name ?? ""}</h2>
					<div className='meta-line'>
						{avgHours !== undefined && avgHours !== null && (
							<span>⏱️ {numberFormat(avgHours)} h médias jogadas</span>
						)}
						{game?.release_date && <span>📅 {game.release_date}</span>}
						{game?.price && <span>💰 {game.price}</span>}
						{metadata?.generated_at && <span>🗓️ {metadata.generated_at}</span>}
					</div>
					{game?.short_description && (
						<p className='description'>{game.short_description}</p>
					)}
				</div>
				{game?.header_image && (
					<img
						src={game.header_image}
						alt={game?.name}
						className='game-cover'
					/>
				)}
			</header>

			<div className='stat-grid'>
				<div className='stat-card'>
					<span>Reviews processadas</span>
					<strong>{integerFormat(summary?.reviews_analyzed ?? 0)}</strong>
				</div>
				<div className='stat-card good'>
					<span>Positivas</span>
					<strong>
						{integerFormat(summary?.positive_count ?? 0)} •
						{summary?.positive_percentage ?? 0}%
					</strong>
				</div>
				<div className='stat-card bad'>
					<span>Negativas</span>
					<strong>
						{integerFormat(summary?.negative_count ?? 0)} •
						{summary?.negative_percentage ?? 0}%
					</strong>
				</div>
				<div className='stat-card neutral'>
					<span>Idioma / limite</span>
					<strong>
						{meta?.language === "brazilian" ? "PT-BR" : meta?.language}
						&nbsp;•&nbsp;
						{integerFormat(meta?.maxReviewsRequested ?? 0)} máx.
					</strong>
				</div>
				{owners && (
					<div className='stat-card highlight'>
						<span>🧾 Estimativa de copias (SteamSpy)</span>
						<strong>{owners}</strong>
					</div>
				)}
				{totalSteamReviews && (
					<div className='stat-card highlight'>
						<span>🗳️ Reviews totais na Steam</span>
						<strong>{integerFormat(totalSteamReviews)}</strong>
					</div>
				)}
			</div>

			<div className='highlights-grid'>
				<div className='highlight-column positive'>
					<h3>✅ O que elogiam</h3>
					{highlights?.positive?.length ? (
						highlights.positive.map((sentence, idx) => (
							<p key={`pos-${idx}`}>“{sentence}”</p>
						))
					) : (
						<p className='muted'>Sem frases suficientes.</p>
					)}
				</div>
				<div className='highlight-column negative'>
					<h3>❌ O que criticam</h3>
					{highlights?.negative?.length ? (
						highlights.negative.map((sentence, idx) => (
							<p key={`neg-${idx}`}>“{sentence}”</p>
						))
					) : (
						<p className='muted'>Sem frases suficientes.</p>
					)}
				</div>
			</div>

			<div className='topics-header'>
				<h3>Temas {topicView === "positive" ? "positivos" : "negativos"}</h3>
				<button
					type='button'
					className='topics-toggle'
					onClick={() =>
						setTopicView((current) =>
							current === "positive" ? "negative" : "positive",
						)
					}
				>
					{topicView === "positive" ? "Ver negativos" : "Ver positivos"}
				</button>
			</div>

			<div className='topics-grid'>
				{orderedTopics.map((topic, idx) => (
					<div
						className={`topic-card ${topicView}`}
						key={`${topic.topic}-${idx}`}
					>
						<div className='topic-header'>
							<strong>{topic.topic}</strong>
							<span>{numberFormat(topic.mentions)} menções</span>
						</div>
						<div className='topic-columns'>
							<div>
								<p className='eyebrow'>{topicLabel}</p>
								{topic.quotes?.length ? (
									topic.quotes.map((sentence, quoteIdx) => (
										<span key={`${topic.topic}-${quoteIdx}`}>{sentence}</span>
									))
								) : (
									<span className='muted'>Sem menções.</span>
								)}
							</div>
						</div>
					</div>
				))}
			</div>
		</section>
	);
}
