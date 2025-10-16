<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { userSignIn, userSignUp } from '$lib/apis/auths';

import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = 'signin';

let name = '';
let email = '';
let password = '';
let confirmPassword = '';

const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirectPath') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

const submitHandler = async () => {
	if (mode === 'signin') {
		await signInHandler();
	} else {
		await signUpHandler();
	}
};

let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] text-white relative" id="auth-page">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-black dark:text-white"
			id="auth-container"
		>
			<div class="w-full px-10 min-h-screen flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<div class="my-auto flex flex-col justify-center items-center">
						<div class=" sm:max-w-md my-auto pb-10 w-full dark:text-gray-100">
							{#if $config?.metadata?.auth_logo_position === 'center'}
								<div class="flex justify-center mb-6">
									<img
										id="logo"
										crossorigin="anonymous"
										src="{WEBUI_BASE_URL}/static/favicon.png"
										class="size-24 rounded-full"
										alt=""
									/>
								</div>
							{/if}
							<form
								class=" flex flex-col justify-center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<div class="mb-1">
									<div class=" text-2xl font-medium">
										{#if $config?.onboarding ?? false}
											{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'signin'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else}
											{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{/if}
									</div>

									{#if $config?.onboarding ?? false}
										<div class="mt-1 text-xs font-medium text-gray-600 dark:text-gray-500">
											ⓘ {$WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</div>
									{/if}
								</div>

								<div class="flex flex-col mt-4">
									{#if mode === 'signup'}
										<div class="mb-2">
											<label for="name" class="text-sm font-medium text-left mb-1 block"
												>{$i18n.t('Name')}</label
											>
											<input
												bind:value={name}
												type="text"
												id="name"
												class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
												autocomplete="name"
												placeholder={$i18n.t('Enter Your Full Name')}
												required
											/>
										</div>
									{/if}

									<div class="mb-2">
										<label for="email" class="text-sm font-medium text-left mb-1 block"
											>{$i18n.t('Email')}</label
										>
										<input
											bind:value={email}
											type="email"
											id="email"
											class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
											autocomplete="email"
											name="email"
											placeholder={$i18n.t('Enter Your Email')}
											required
										/>
									</div>

									<div>
										<label for="password" class="text-sm font-medium text-left mb-1 block"
											>{$i18n.t('Password')}</label
										>
										<SensitiveInput
											bind:value={password}
											type="password"
											id="password"
											class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
											placeholder={$i18n.t('Enter Your Password')}
											autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
											name="password"
											required
										/>
									</div>

									{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
										<div class="mt-2">
											<label for="confirm-password" class="text-sm font-medium text-left mb-1 block"
												>{$i18n.t('Confirm Password')}</label
											>
											<SensitiveInput
												bind:value={confirmPassword}
												type="password"
												id="confirm-password"
												class="my-0.5 w-full text-sm outline-hidden bg-transparent"
												placeholder={$i18n.t('Confirm Your Password')}
												autocomplete="new-password"
												name="confirm-password"
												required
											/>
										</div>
									{/if}
								</div>
								<div class="mt-5">
									<button
										class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										type="submit"
									>
										{mode === 'signin'
											? $i18n.t('Sign in')
											: ($config?.onboarding ?? false)
												? $i18n.t('Create Admin Account')
												: $i18n.t('Create Account')}
									</button>

									{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
										<div class=" mt-4 text-sm text-center">
											{mode === 'signin'
												? $i18n.t("Don't have an account?")
												: $i18n.t('Already have an account?')}

											<button
												class=" font-medium underline"
												type="button"
												on:click={() => {
													mode = mode === 'signin' ? 'signup' : 'signin';
												}}
											>
												{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
											</button>
										</div>
									{/if}
								</div>
							</form>
						</div>
						{#if $config?.metadata?.login_footer}
							<div class="max-w-3xl mx-auto">
								<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if !$config?.metadata?.auth_logo_position}
			<div class="fixed m-10 z-50">
				<div class="flex space-x-2">
					<div class=" self-center">
						<img
							id="logo"
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class=" w-6 rounded-full"
							alt=""
						/>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>
