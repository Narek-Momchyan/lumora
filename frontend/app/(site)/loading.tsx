import Spinner from '@/components/Spinner'

// Shown in the page area while a page of the site loads. The header and the sidebar stay where they are, so
// moving between pages feels immediate.
export default function Loading() {
  return (
    <div aria-busy="true" className="flex min-h-[50dvh] items-center justify-center">
      <Spinner />
    </div>
  )
}
