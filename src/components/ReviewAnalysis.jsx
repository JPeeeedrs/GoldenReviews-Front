import { useMemo } from "react";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

export default function ReviewAnalysis({ data }) {
	if (!data) return null;

	const { game, summary, highlights, topics, keywords } = data;

	const orderedTopics = useMemo(() => {
		if (!topics) return [];
		return [...topics]
			.sort((a, b) => {
				const totalA = a.positive.count + a.negative.count;
				const totalB = b.positive.count + b.negative.count;
				return totalB - totalA;
			})
			.slice(0, 8);
	}, [topics]);

	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;

	return (
		<section className='analysis'>
			<header className='analysis-hero'>
				<div>
					<p className='eyebrow'>Jogo em análise</p>
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
				<div>
					<h3>✅ O que elogiam</h3>
					{highlights?.positivo?.length ? (
						highlights.positivo.map((sentence, idx) => (
							<p key={`pos-${idx}`}>“{sentence}”</p>
						))
					) : (
						<p className='muted'>Sem frases suficientes.</p>
					)}
				</div>
				<div>
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

			<div className='topics-grid'>
				{orderedTopics.map((topic) => (
					<div className='topic-card' key={topic.name}>
						<div className='topic-header'>
							<strong>{topic.name}</strong>
							<span>
								{numberFormat(topic.positive.count + topic.negative.count)}{" "}
								menções
							</span>
						</div>
						<div className='topic-columns'>
							<div>
								<p className='eyebrow'>Positivos</p>
								{topic.positive.examples.length ? (
									topic.positive.examples.map((sentence, idx) => (
										<span key={`tpos-${topic.name}-${idx}`}>{sentence}</span>
									))
								) : (
									<span className='muted'>Sem menções.</span>
								)}
							</div>

							<div>
								<p className='eyebrow'>Negativos</p>
								{topic.negative.examples.length ? (
									topic.negative.examples.map((sentence, idx) => (
										<span key={`tneg-${topic.name}-${idx}`}>{sentence}</span>
									))
								) : (
									<span className='muted'>Sem menções.</span>
								)}
							</div>
						</div>
					</div>
				))}
			</div>

			<div className='keywords-grid'>
				<div>
					<h3>🔍 Termos positivos</h3>
					<ul>
						{keywords?.positive?.length ? (
							keywords.positive.slice(0, 18).map(([phrase, count]) => (
								<li key={phrase}>
									<span>{phrase}</span>
									<strong>{count}×</strong>
								</li>
							))
						) : (
							<li className='muted'>Nada encontrado.</li>
						)}
					</ul>
				</div>
				<div>
					<h3>⚠️ Termos negativos</h3>
					<ul>
						{keywords?.negative?.length ? (
							keywords.negative.slice(0, 18).map(([phrase, count]) => (
								<li key={phrase}>
									<span>{phrase}</span>
									<strong>{count}×</strong>
								</li>
							))
						) : (
							<li className='muted'>Nada encontrado.</li>
						)}
					</ul>
				</div>
			</div>
		</section>
	);
}
