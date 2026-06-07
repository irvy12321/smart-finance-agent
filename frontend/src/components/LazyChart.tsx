import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

const Chart = lazy(() => import("./Chart"));

interface Props {
  labels: string[];
  values: number[];
  title?: string;
  type?: "line" | "bar";
  color?: string;
}

export default function LazyChart(props: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ minHeight: 320 }}>
      {visible ? (
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-[300px]">
              <Loader2 className="w-6 h-6 text-primary-500 animate-spin mr-2" />
              <span className="text-sm text-primary-400">Loading chart...</span>
            </div>
          }
        >
          <Chart {...props} />
        </Suspense>
      ) : (
        <div className="flex items-center justify-center h-[300px] text-primary-500 text-sm">
          Chart will load when visible...
        </div>
      )}
    </div>
  );
}
