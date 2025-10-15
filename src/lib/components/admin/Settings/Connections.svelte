<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
import {
	getOpenAIConfig,
	updateOpenAIConfig,
	getOpenAIModels,
	type OpenAIKeyDescriptor,
	type OpenAIConfigResponse
} from '$lib/apis/openai';
	import { getModels as _getModels, getBackendConfig } from '$lib/apis';
	import { getConnectionsConfig, setConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
			false,
			true
		);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

let OPENAI_API_KEYS = [''];
let OPENAI_API_KEY_KEEP: boolean[] = [];
let OPENAI_API_KEY_METADATA: OpenAIKeyDescriptor[] = [];
let OPENAI_API_BASE_URLS = [''];
let OPENAI_API_CONFIGS = {};

let openAIKeySecurityMeta = {
	persistence_enabled: false,
	encryption_enabled: false
};

let allowedOpenAIBaseUrls: string[] = [];

const defaultKeyDescriptor = (): OpenAIKeyDescriptor => ({
	has_value: false,
	masked: '',
	fingerprint: null
});

const maskKeyForDisplay = (key: string = '') => {
	if (!key) return '';
	const visible = key.slice(-4);
	const maskedLength = Math.max(key.length - visible.length, 4);
	return `${'*'.repeat(maskedLength)}${visible}`;
};

const ensureOpenAIArrayLengths = () => {
	if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
	} else if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEYS = [
			...OPENAI_API_KEYS,
			...Array(OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length).fill('')
		];
	}

	if (OPENAI_API_KEY_KEEP.length > OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEY_KEEP = OPENAI_API_KEY_KEEP.slice(0, OPENAI_API_BASE_URLS.length);
	} else if (OPENAI_API_KEY_KEEP.length < OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEY_KEEP = [
			...OPENAI_API_KEY_KEEP,
			...Array(OPENAI_API_BASE_URLS.length - OPENAI_API_KEY_KEEP.length).fill(false)
		];
	}

	if (OPENAI_API_KEY_METADATA.length > OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEY_METADATA = OPENAI_API_KEY_METADATA.slice(0, OPENAI_API_BASE_URLS.length);
	} else if (OPENAI_API_KEY_METADATA.length < OPENAI_API_BASE_URLS.length) {
		OPENAI_API_KEY_METADATA = [
			...OPENAI_API_KEY_METADATA,
			...Array(OPENAI_API_BASE_URLS.length - OPENAI_API_KEY_METADATA.length).fill(undefined)
		].map((item) => item ?? defaultKeyDescriptor());
	} else {
		OPENAI_API_KEY_METADATA = OPENAI_API_KEY_METADATA.map((item) => item ?? defaultKeyDescriptor());
	}
};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let connectionsConfig = null;

	let pipelineUrls = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;

const updateOpenAIHandler = async () => {
	if (ENABLE_OPENAI_API !== null) {
		// Remove trailing slashes
		OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));
		ensureOpenAIArrayLengths();

		const keyPayloads = OPENAI_API_BASE_URLS.map((_, idx) => {
			if (OPENAI_API_KEY_KEEP[idx]) {
				return { keep: true };
			}

			return { value: OPENAI_API_KEYS[idx] ?? '' };
		});

		const res = await updateOpenAIConfig(localStorage.token, {
			ENABLE_OPENAI_API: ENABLE_OPENAI_API,
			OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
			OPENAI_API_KEYS: keyPayloads,
			OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			OPENAI_API_BASE_URLS = res.OPENAI_API_BASE_URLS;
			OPENAI_API_CONFIGS = res.OPENAI_API_CONFIGS;
			OPENAI_API_KEY_METADATA = res.OPENAI_API_KEYS ?? [];
			OPENAI_API_KEYS = OPENAI_API_BASE_URLS.map(() => '');
			OPENAI_API_KEY_KEEP = OPENAI_API_KEY_METADATA.map((item) => item?.has_value ?? false);
			openAIKeySecurityMeta = {
				persistence_enabled: res.OPENAI_API_KEYS_METADATA?.persistence_enabled ?? false,
				encryption_enabled: res.OPENAI_API_KEYS_METADATA?.encryption_enabled ?? false
			};
			allowedOpenAIBaseUrls = res.OPENAI_ALLOWED_BASE_URLS ?? allowedOpenAIBaseUrls;
			ensureOpenAIArrayLengths();
			toast.success($i18n.t('OpenAI API settings updated'));
			await models.set(await getModels());
		}
	}
};

const updateOllamaHandler = async () => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove trailing slashes
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateConnectionsHandler = async () => {
		const res = await setConnectionsConfig(localStorage.token, connectionsConfig).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Connections settings updated'));
			await models.set(await getModels());
			await config.set(await getBackendConfig());
		}
	};

const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key ?? ''];
		OPENAI_API_KEY_KEEP = [
			...OPENAI_API_KEY_KEEP,
			Boolean(connection.hasStoredKey && !connection.keyChanged)
		];
		OPENAI_API_KEY_METADATA = [
			...OPENAI_API_KEY_METADATA,
			connection.key
				? {
					masked: maskKeyForDisplay(connection.key),
					has_value: true,
					fingerprint: null
				}
				: defaultKeyDescriptor()
		];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length - 1] = connection.config;

		ensureOpenAIArrayLengths();

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length - 1] = {
			...connection.config,
			key: connection.key
		};

		await updateOllamaHandler();
	};

	onMount(async () => {
	if ($user?.role === 'admin') {
		let ollamaConfig = {};
		let openaiConfig: OpenAIConfigResponse;

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})(),
				(async () => {
					connectionsConfig = await getConnectionsConfig(localStorage.token);
				})()
			]);

			ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
			ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;

			OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
			OPENAI_API_KEY_METADATA = (openaiConfig.OPENAI_API_KEYS ?? []).map((item) =>
				item ?? defaultKeyDescriptor()
			);
			OPENAI_API_KEYS = OPENAI_API_BASE_URLS.map(() => '');
			OPENAI_API_KEY_KEEP = OPENAI_API_BASE_URLS.map(
				(_, idx) => OPENAI_API_KEY_METADATA[idx]?.has_value ?? false
			);
			OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;
			openAIKeySecurityMeta = {
				persistence_enabled: openaiConfig.OPENAI_API_KEYS_METADATA?.persistence_enabled ?? false,
				encryption_enabled: openaiConfig.OPENAI_API_KEYS_METADATA?.encryption_enabled ?? false
			};
			allowedOpenAIBaseUrls = openaiConfig.OPENAI_ALLOWED_BASE_URLS ?? [];
			ensureOpenAIArrayLengths();

			OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
			OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

			if (ENABLE_OPENAI_API) {
				// get url and idx
				for (const [idx, url] of OPENAI_API_BASE_URLS.entries()) {
					if (!OPENAI_API_CONFIGS[idx]) {
						// Legacy support, url as key
						OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[url] || {};
					}
				}

				OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
					OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[idx] || {};
					if (!(OPENAI_API_CONFIGS[idx]?.enable ?? true)) {
						return;
					}
					const res = await getOpenAIModels(localStorage.token, idx);
					if (res.pipelines) {
						pipelineUrls[url] = true;
					}
				});
			}

			if (ENABLE_OLLAMA_API) {
				for (const [idx, url] of OLLAMA_BASE_URLS.entries()) {
					if (!OLLAMA_API_CONFIGS[idx]) {
						OLLAMA_API_CONFIGS[idx] = OLLAMA_API_CONFIGS[url] || {};
					}
				}
			}
		}
	});

	const submitHandler = async () => {
		updateOpenAIHandler();
		updateOllamaHandler();

		dispatch('save');

		await config.set(await getBackendConfig());
	};
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	allowedUrls={allowedOpenAIBaseUrls}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null}
			<div class="mb-3.5">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="my-2">
					<div class="mt-2 space-y-2">
						<div class="flex justify-between items-center text-sm">
							<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

							<div class="flex items-center">
								<div class="">
									<Switch
										bind:state={ENABLE_OPENAI_API}
										on:change={async () => {
											updateOpenAIHandler();
										}}
									/>
								</div>
							</div>
						</div>

						{#if ENABLE_OPENAI_API}
							<div class="">
				<div class="flex justify-between items-center">
					<div class="font-medium text-xs">{$i18n.t('Manage OpenAI API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											class="px-1"
											on:click={() => {
												showAddOpenAIConnectionModal = true;
											}}
											type="button"
										>
											<Plus />
										</button>
									</Tooltip>
								</div>

				<div class="flex flex-col gap-1.5 mt-1.5">
					{#each OPENAI_API_BASE_URLS as url, idx}
						<OpenAIConnection
							bind:url={OPENAI_API_BASE_URLS[idx]}
							bind:keyValue={OPENAI_API_KEYS[idx]}
							hasStoredKey={OPENAI_API_KEY_KEEP[idx]}
							maskedKey={OPENAI_API_KEY_METADATA[idx]?.masked ?? ''}
							allowedUrls={allowedOpenAIBaseUrls}
							bind:config={OPENAI_API_CONFIGS[idx]}
							pipeline={pipelineUrls[url] ? true : false}
							onSubmit={(connection) => {
								OPENAI_API_BASE_URLS[idx] = connection.url;
								OPENAI_API_CONFIGS[idx] = connection.config;
								if (connection.keyChanged) {
									OPENAI_API_KEYS[idx] = connection.key ?? '';
									OPENAI_API_KEY_KEEP[idx] = false;
									OPENAI_API_KEY_METADATA[idx] = connection.key
										? {
											masked: maskKeyForDisplay(connection.key),
											has_value: true,
											fingerprint: null
										}
										: defaultKeyDescriptor();
								} else {
									OPENAI_API_KEYS[idx] = '';
									OPENAI_API_KEY_KEEP[idx] = connection.hasStoredKey ?? false;
									OPENAI_API_KEY_METADATA[idx] = {
										...(OPENAI_API_KEY_METADATA[idx] ?? defaultKeyDescriptor()),
										has_value: connection.hasStoredKey ?? false
									};
								}
								ensureOpenAIArrayLengths();
								updateOpenAIHandler();
							}}
							onDelete={() => {
								OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
									(url, urlIdx) => idx !== urlIdx
								);
								OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);
								OPENAI_API_KEY_KEEP = OPENAI_API_KEY_KEEP.filter((keep, keepIdx) => idx !== keepIdx);
								OPENAI_API_KEY_METADATA = OPENAI_API_KEY_METADATA.filter(
									(_, metaIdx) => idx !== metaIdx
								);

								let newConfig = {};
								OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
									newConfig[newIdx] =
										OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
								});
								OPENAI_API_CONFIGS = newConfig;
								ensureOpenAIArrayLengths();
								updateOpenAIHandler();
							}}
						/>
					{/each}
				</div>

				{#if allowedOpenAIBaseUrls.length > 0}
					<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Only the following OpenAI endpoints are allowed: {{endpoints}}', {
							endpoints: allowedOpenAIBaseUrls.join(', ')
						})}
					</div>
				{/if}

				{#if !openAIKeySecurityMeta.encryption_enabled}
					<div class="mt-1 text-xs text-amber-600 dark:text-amber-400">
						{$i18n.t('CONFIG_ENCRYPTION_KEY is not set, so stored API keys remain in-memory only and are cleared on restart.')}
					</div>
				{/if}
							</div>
						{/if}
					</div>
				</div>

				<div class=" my-2">
					<div class="flex justify-between items-center text-sm mb-2">
						<div class="  font-medium">{$i18n.t('Ollama API')}</div>

						<div class="mt-1">
							<Switch
								bind:state={ENABLE_OLLAMA_API}
								on:change={async () => {
									updateOllamaHandler();
								}}
							/>
						</div>
					</div>

					{#if ENABLE_OLLAMA_API}
						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium text-xs">{$i18n.t('Manage Ollama API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOllamaConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex w-full gap-1.5">
								<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
									{#each OLLAMA_BASE_URLS as url, idx}
										<OllamaConnection
											bind:url={OLLAMA_BASE_URLS[idx]}
											bind:config={OLLAMA_API_CONFIGS[idx]}
											{idx}
											onSubmit={() => {
												updateOllamaHandler();
											}}
											onDelete={() => {
												OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);

												let newConfig = {};
												OLLAMA_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OLLAMA_API_CONFIGS = newConfig;
											}}
										/>
									{/each}
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Trouble accessing Ollama?')}
								<a
									class=" text-gray-300 font-medium underline"
									href="https://github.com/open-webui/open-webui#troubleshooting"
									target="_blank"
								>
									{$i18n.t('Click here for help.')}
								</a>
							</div>
						</div>
					{/if}
				</div>

				<div class="my-2">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('Direct Connections')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_DIRECT_CONNECTIONS}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t(
							'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
						)}
					</div>
				</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="my-2">
					<div class="flex justify-between items-center text-sm">
						<div class=" text-xs font-medium">{$i18n.t('Cache Base Model List')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_BASE_MODELS_CACHE}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t(
							'Base Model List Cache speeds up access by fetching base models only at startup or on settings save—faster, but may not show recent base model changes.'
						)}
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
