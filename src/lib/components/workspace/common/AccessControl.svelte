<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

export let onChange: (value: any) => void = () => {};
export let accessRoles = ['read']; // kept for API compatibility
export let accessControl: any = null;
export let allowPublic = false;

const PUBLIC_SHARING_ENABLED = false;
let effectiveAllowPublic = false;

$: effectiveAllowPublic = PUBLIC_SHARING_ENABLED && allowPublic;

	const PRIVATE_TEMPLATE = {
		read: {
			group_ids: [],
			user_ids: []
		},
		write: {
			group_ids: [],
			user_ids: []
		}
	};

const applyChange = (value: any) => {
	accessControl = value === null ? null : JSON.parse(JSON.stringify(value));
	onChange(accessControl);
};

onMount(() => {
	let mutated = false;
	if (!effectiveAllowPublic) {
		applyChange(PRIVATE_TEMPLATE);
		mutated = true;
	} else if (accessControl === undefined) {
		applyChange(null);
		mutated = true;
	}

	if (!mutated) {
		onChange(accessControl);
	}
});
</script>

<div class="rounded-lg flex flex-col gap-2">
	<div>
		<div class="text-sm font-semibold mb-1.5">{$i18n.t('Visibility')}</div>

		<div class="flex gap-2.5 items-center mb-1">
			<div>
				<div class="p-2 bg-black/5 dark:bg-white/5 rounded-full">
					{#if accessControl !== null}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.13-.132a1.125 1.125 0 011.3-.21l.603.302a.809.809 0 001.086-1.086L14.25 7.5l1.256-.837a4.5 4.5 0 001.528-1.732l.146-.292M6.115 5.19A9 9 0 1017.18 4.64M6.115 5.19A8.965 8.965 0 0112 3c1.929 0 3.716.607 5.18 1.64"
							/>
						</svg>
					{/if}
				</div>
			</div>

				{#if effectiveAllowPublic}
					<div>
						<select
						id="access-select"
						class="outline-hidden bg-transparent text-sm font-medium rounded-lg block w-fit pr-10 max-w-full placeholder-gray-400"
						value={accessControl !== null ? 'private' : 'public'}
						on:change={(e) => {
							if (e.target.value === 'public') {
								applyChange(null);
							} else {
								applyChange(PRIVATE_TEMPLATE);
							}
						}}
					>
						<option class="text-gray-700" value="private">{$i18n.t('Private')}</option>
						<option class="text-gray-700" value="public">{$i18n.t('Public')}</option>
					</select>

					<div class="text-xs text-gray-400 font-medium">
						{#if accessControl !== null}
							{$i18n.t('Only you can access this resource')}
				{:else}
							{$i18n.t('Accessible to anyone visiting this instance')}
						{/if}
					</div>
				</div>
			{:else}
				<div class="text-xs text-gray-400 font-medium">
					{$i18n.t('Access is restricted to the local user.')}
				</div>
			{/if}
		</div>
	</div>

	{#if accessControl !== null}
		<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5">
			{$i18n.t('Fine-grained user or group controls are disabled in single-user mode.')}
		</div>
	{/if}
</div>
