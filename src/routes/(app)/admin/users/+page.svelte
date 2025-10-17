<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
</script>

<div class="px-6 py-10 text-center text-sm text-gray-500 dark:text-gray-400">
	<p>{$i18n.t('User management is disabled in this single-user build.')}</p>
</div>
