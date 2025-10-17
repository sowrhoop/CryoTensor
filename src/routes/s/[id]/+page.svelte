<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	onMount(() => {
		// Redirect back to the main app after showing the message briefly.
		setTimeout(() => goto('/'), 1500);
	});
</script>

<svelte:head>
	<title>{$i18n.t('Sharing Disabled')}</title>
</svelte:head>

<div class="h-screen max-h-[100dvh] w-full flex flex-col items-center justify-center bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100 px-6 text-center space-y-4">
	<h1 class="text-2xl font-semibold">{$i18n.t('Sharing Disabled')}</h1>
	<p class="text-sm text-gray-500 dark:text-gray-400 max-w-md">
		{$i18n.t('Public chat links are disabled in this single-user build. You will be returned to the home screen shortly.')}
	</p>
	<button
		class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
		on:click={() => goto('/')}
	>
		{$i18n.t('Go to Home')}
	</button>
</div>
