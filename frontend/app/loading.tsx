import Image from 'next/image'
import Spinner from '@/components/Spinner'
import { getLogo } from '@/lib/content'

// Shown while the site opens (the first load, and the login page): the logo from the admin inside a turning
// ring, in the middle of the screen. Pages inside the site have their own, smaller one (app/(site)/loading.tsx),
// so moving between pages keeps the header and the sidebar.
export default async function Loading() {
  const logo = await getLogo()

  return (
    <div aria-busy="true" className="flex min-h-dvh flex-col items-center justify-center gap-4">
      <div className="relative flex size-24 items-center justify-center">
        <div className="absolute inset-0">
          <Spinner size="lg" />
        </div>
        {logo && <Image src={logo.image} alt="" width={40} height={40} unoptimized priority />}
      </div>
      {logo && <p className="font-heading text-lg font-bold text-text">{logo.name}</p>}
    </div>
  )
}
