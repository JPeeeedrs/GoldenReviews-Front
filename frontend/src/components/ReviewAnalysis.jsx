import { useMemo, useState } from "react";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

const integerFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);

export default function ReviewAnalysis({ data }) {
	const [topicView, setTopicView] = useState("positive");

	const orderedTopics = useMemo(() => {
		if (!data?.topics) return [];
		const topicsArray = data.topics[topicView] || [];
		return topicsArray.slice(0, 10);
	}, [data?.topics, topicView]);

	if (!data) return null;

	const game = data.game || {};
	const summary = data.summary || {};
	const metadata = data.metadata || {};
	const meta = data.meta || {};

	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;
	const avgHours = summary?.avg_hours;

	return (
		<section className='analysis'>
			<header className='analysis-hero'>
				<div>
					<p className='eyebrow'>GOLDEN REVIEWS • JOGO EM ANÁLISE</p>
					<h2>{game?.name ?? ""}</h2>
					<div className='meta-line'>
						{summary?.overall_score !== undefined && (
							<span>
								⭐ {numberFormat(summary.overall_score)} Score Geral (IA)
							</span>
						)}
						{avgHours !== undefined && avgHours !== null && (
							<span>⏱️ {numberFormat(avgHours)} h médias jogadas</span>
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
				{/* Restaurado 100% igual a imagem */}
				<div className='stat-card'>
					<span>Reviews processadas</span>
					<strong>{integerFormat(summary?.reviews_analyzed ?? 0)}</strong>
				</div>

				<div className='stat-card good'>
					<span>Positivas</span>
					<strong>
						{integerFormat(summary?.positive_count ?? 0)} •{" "}
						{summary?.positive_percentage ?? 0}%
					</strong>
				</div>

				<div className='stat-card bad'>
					<span>Negativas</span>
					<strong>
						{integerFormat(summary?.negative_count ?? 0)} •{" "}
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
						<span>🧾 Estimativa de cópias (SteamSpy)</span>
						<strong>{owners}</strong>
					</div>
				)}

				{totalSteamReviews && (
					<div className='stat-card highlight'>
						<span>🗳️ Reviews totais na Steam</span>
						<strong>{integerFormat(totalSteamReviews)}</strong>
					</div>
				)}

				{/* Card do ABSA adicionado sem quebrar os originais */}
				{metadata?.processing_time_seconds !== undefined && (
					<div className='stat-card neutral'>
						<span>Processamento IA</span>
						<strong>
							{metadata.processing_time_seconds}s &nbsp;•&nbsp;
							{metadata.model_version || "BERTopic"}
						</strong>
					</div>
				)}
			</div>

			<div className='topics-header'>
				<h3>Tópicos {topicView === "positive" ? "positivos" : "negativos"}</h3>
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
				{orderedTopics.map((topic, idx) => {
					const examples = topic?.quotes ?? [];
					const count = topic?.mentions ?? 0;
					const keywords = topic?.keywords?.slice(0, 3).join(", ");

					return (
						<div className={`topic-card ${topicView}`} key={`topic-${idx}`}>
							<div className='topic-header'>
								<strong>{topic.topic?.toUpperCase()}</strong>
								<span>{integerFormat(count)} menções</span>
							</div>
							<div className='topic-columns'>
								<div>
									<p className='eyebrow'>
										Score semântico: {numberFormat(topic.score)} / 5.0
									</p>
									<p
										className='eyebrow'
										style={{ marginTop: "-8px", fontStyle: "italic" }}
									>
										[{keywords}]
									</p>

									{examples.length ? (
										examples.map((sentence, i) => (
											<span key={`q-${i}`}>"{sentence}"</span>
										))
									) : (
										<span className='muted'>Sem frases representativas.</span>
									)}
								</div>
							</div>
						</div>
					);
				})}
				{orderedTopics.length === 0 && (
					<p className='muted'>Nenhum tópico encontrado para este viés.</p>
				)}
			</div>
		</section>
	);
}
