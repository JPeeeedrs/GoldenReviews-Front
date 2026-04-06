import "../styles/search.css";

export default function SearchBox({ value, onChange, onClear, showClear }) {
	return (
		<div className='search-box'>
			<label>Buscar jogo</label>

			<div className='search-input-wrap'>
				<input
					type='text'
					placeholder='Digite o nome de um jogo...'
					value={value}
					onChange={(e) => onChange(e.target.value)}
				/>

				{showClear && (
					<button
						type='button'
						className='clear-search-btn'
						onClick={onClear}
						aria-label='Limpar busca e seleção'
						title='Limpar busca e seleção'
					>
						X
					</button>
				)}
			</div>

			<span className='hint'>Autocomplete visual em tempo real</span>
		</div>
	);
}
