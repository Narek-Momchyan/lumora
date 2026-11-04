// The page's name in the top bar, as in the design: "Neon Crash", "Lumora Roulette" ...
export default function PageTitle({ children }: { children: string }) {
  return <h1 className="min-w-0 truncate font-heading text-xl font-bold sm:text-2xl lg:text-[26px]">{children}</h1>
}
