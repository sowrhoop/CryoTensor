<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let chatInputElement: HTMLTextAreaElement | null = null;
	export let acceptFiles = false; // kept for API compatibility
	export let inputLoading = false;
	export let showFormattingToolbar = false; // unused but preserved for compatibility
	export let onSubmit: Function = () => {};
	export let onStop: Function = () => {};

	let value = '';

	const submit = async () => {
		const content = value.trim();
		if (!content || inputLoading) {
			return;
		}

		await onSubmit({
			content,
			data: {}
		});

		value = '';
		dispatch('submit');
	};

	const handleKeydown = async (event: KeyboardEvent) => {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			await submit();
		}
	};
</script>

<div class="message-input">
	<div class="flex flex-col gap-2 bg-gray-50 dark:bg-gray-900/40 rounded-2xl px-3.5 py-3">
		{#if showFormattingToolbar}
			<slot name="menu" />
		{:else}
			<div class="flex justify-between items-center">
				<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
					<slot name="menu" />
				</div>
			</div>
		{/if}

		<textarea
			bind:this={chatInputElement}
			bind:value
			class="w-full resize-none bg-transparent text-sm focus:outline-hidden max-h-40"
			rows={3}
			placeholder={$i18n.t('Type here...')}
			on:keydown={handleKeydown}
			aria-label={$i18n.t('Chat input')}
		></textarea>

		<div class="flex justify-end items-center gap-2">
			{#if inputLoading}
				<Tooltip content={$i18n.t('Stop')}>
					<button
						type="button"
						class="inline-flex items-center justify-center rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-200 p-2 transition hover:bg-gray-300 dark:hover:bg-gray-700"
						on:click={() => onStop?.()}
					>
						<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
							<path d="M10 18.75a8.75 8.75 0 1 0 0-17.5 8.75 8.75 0 0 0 0 17.5Zm3.25-11.5c0-.69-.56-1.25-1.25-1.25h-4a1.25 1.25 0 0 0-1.25 1.25v4a1.25 1.25 0 0 0 1.25 1.25h4a1.25 1.25 0 0 0 1.25-1.25v-4Z" />
						</svg>
					</button>
				</Tooltip>
			{:else}
				<Tooltip content={$i18n.t('Send message')}>
					<button
						type="button"
						class="inline-flex items-center justify-center rounded-full bg-black text-white dark:bg-white dark:text-black p-2 transition disabled:opacity-60 disabled:cursor-not-allowed"
						on:click={submit}
						disabled={value.trim() === ''}
					>
						<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
							<path d="M2.62 2.223a.75.75 0 0 0-.938.938l2.35 8.225a1.5 1.5 0 0 0 1.086 1.06l3.177.846a.25.25 0 0 1 .183.182l.845 3.177a1.5 1.5 0 0 0 1.06 1.086l8.226 2.35a.75.75 0 0 0 .937-.938l-2.35-8.225a1.5 1.5 0 0 0-1.06-1.06L8.277 9.04a.25.25 0 0 1-.182-.183l-.846-3.176a1.5 1.5 0 0 0-1.06-1.06L2.62 2.223Z" />
						</svg>
					</button>
				</Tooltip>
			{/if}
		</div>
	</div>
</div>

<style>
	.message-input textarea {
		font-family: inherit;
	}
</style>
