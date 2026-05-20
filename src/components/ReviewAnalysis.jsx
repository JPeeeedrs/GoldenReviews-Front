import { useMemo, useState } from "react";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

export default function ReviewAnalysis({ data }) {
	const [topicView, setTopicView] = useState("positive");

	const orderedTopics = useMemo(() => {
		if (!data?.topics) return [];

		const topics = data.topics;
		if (!topics) return [];
		return [...topics]
			.filter((topic) => (topic?.[topicView]?.count ?? 0) > 0)
			.sort((a, b) => {
				const countA = a?.[topicView]?.count ?? 0;
				const countB = b?.[topicView]?.count ?? 0;
				return countB - countA;
			})
			.slice(0, 8);
	}, [data?.topics, topicView]);

	if (!data) return null;

	const { game, summary, highlights } = data;
	const topicLabel = topicView === "positive" ? "Positivos" : "Negativos";

	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;

	return (
		<section className='analysis'>
			<header className='analysis-hero'>
				<div>
					<p className='eyebrow'>Golden Reviews • jogo em análise</p>
					<h2>{game?.name ?? ""}</h2>
					<div className='meta-line'>
						{summary?.avg_hours !== undefined && (
							<span>⏱️ {numberFormat(summary.avg_hours)} h médias jogadas</span>
						)}
						{game?.release_date && <span>📅 {game.release_date}</span>}
						{game?.price && <span>💰 {game.price}</span>}
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
					<strong>{numberFormat(summary?.collected ?? 0)}</strong>
				</div>
				<div className='stat-card good'>
					<span>Positivas</span>
					<strong>
						{numberFormat(summary?.positive?.count ?? 0)} •
						{summary?.positive?.percent ?? 0}%
					</strong>
				</div>
				<div className='stat-card bad'>
					<span>Negativas</span>
					<strong>
						{numberFormat(summary?.negative?.count ?? 0)} •
						{summary?.negative?.percent ?? 0}%
					</strong>
				</div>
				<div className='stat-card neutral'>
					<span>Idioma / limite</span>
					<strong>
						{data.meta?.language === "brazilian"
							? "PT-BR"
							: data.meta?.language}
						&nbsp;•&nbsp;
						{numberFormat(data.meta?.maxReviewsRequested ?? 0)} máx.
					</strong>
				</div>
				{owners && (
					<div className='stat-card highlight'>
						<span>🧾 Estimativa de cópias (SteamSpy)</span>
						<strong>{owners}</strong>
					</div>
				)}
				{totalSteamReviews && (
					<div className='stat-card highlight'>
						<span>🗳️ Reviews totais na Steam</span>
						<strong>{numberFormat(totalSteamReviews)}</strong>
					</div>
				)}
			</div>

			<div className='highlights-grid'>
				<div className='highlight-column positive'>
					<h3>✅ O que elogiam</h3>
					{highlights?.positivo?.length ? (
						highlights.positivo.map((sentence, idx) => (
							<p key={`pos-${idx}`}>“{sentence}”</p>
						))
					) : (
						<p className='muted'>Sem frases suficientes.</p>
					)}
				</div>
				<div className='highlight-column negative'>
					<h3>❌ O que criticam</h3>
					{highlights?.negativo?.length ? (
						highlights.negativo.map((sentence, idx) => (
							<p key={`neg-${idx}`}>“{sentence}”</p>
						))
					) : (
						<p className='muted'>Sem frases suficientes.</p>
					)}
				</div>
			</div>

			<div className='topics-header'>
				<h3>Topicos {topicView === "positive" ? "positivos" : "negativos"}</h3>
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
				{orderedTopics.map((topic) => {
					const examples = topic?.[topicView]?.examples ?? [];
					const count = topic?.[topicView]?.count ?? 0;

					return (
						<div className={`topic-card ${topicView}`} key={topic.name}>
							<div className='topic-header'>
								<strong>{topic.name}</strong>
								<span>{numberFormat(count)} menções</span>
							</div>
							<div className='topic-columns'>
								<div>
									<p className='eyebrow'>{topicLabel}</p>
									{examples.length ? (
										examples.map((sentence, idx) => (
											<span key={`t${topicView}-${topic.name}-${idx}`}>
												{sentence}
											</span>
										))
									) : (
										<span className='muted'>Sem menções.</span>
									)}
								</div>
							</div>
						</div>
					);
				})}
			</div>
		</section>
	);
}
