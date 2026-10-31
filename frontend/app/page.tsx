import Logo from '@/components/Logo'
import { getLoginPageLabels, getLogo } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export default async function Home() {
  const [logo, labels] = await Promise.all([getLogo(), getLoginPageLabels(await displayLang())])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2">
      <Logo logo={logo} />
      <p className="text-muted">{labels.footer_note}</p>
    </main>
  )
}
