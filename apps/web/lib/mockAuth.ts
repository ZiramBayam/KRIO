// MOCK — tunggu backend #36 (@scientivan). Ganti ke signIn()/api asli saat endpoint tersedia.

export interface RegisterPayload {
  name: string;
  email: string;
  company: string;
  password: string;
}

export async function mockRegister(_data: RegisterPayload): Promise<void> {
  // Simulasi jeda jaringan
  await new Promise((resolve) => setTimeout(resolve, 600));
}
