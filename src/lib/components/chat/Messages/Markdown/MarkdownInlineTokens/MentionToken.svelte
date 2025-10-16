<script lang="ts">
	import type { Token } from 'marked';
	import { getContext } from 'svelte';

	import { goto } from '$app/navigation';
	import { models } from '$lib/stores';

	const i18n = getContext('i18n');

	export let token: Token;

	let triggerChar = '';
	let label = '';

	let idType = null;
	let id = '';

	$: if (token) {
		init();
	}

	const init = () => {
		const _id = token?.id;
		// split by : and take first part as idType and second part as id

		const parts = _id?.split(':');
		if (parts) {
			idType = parts[0];
			id = parts.slice(1).join(':'); // in case id contains ':'
		} else {
			idType = null;
			id = _id;
		}

		label = token?.label ?? id;
		triggerChar = token?.triggerChar ?? '@';

		if (triggerChar === '#') {
			// No channel support in pared-down build; fall back to label as-is
			if (!label) {
				label = $i18n.t('Unknown');
			}
		} else if (triggerChar === '@') {
			if (idType === 'U') {
				// User
			} else if (idType === 'M') {
				// Model
				const model = $models.find((m) => m.id === id);
				if (model) {
					label = model.name;
				} else {
					label = $i18n.t('Unknown');
				}
			}
		}
	};
</script>

<span
	class="mention cursor-pointer"
	on:click={async () => {
		if (triggerChar === '@' && idType === 'M') {
			await goto(`/?model=${id}`);
		}
	}}
>
	{triggerChar}{label}
</span>
