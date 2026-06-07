import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler
);

interface Props {
  labels: string[];
  values: number[];
  title?: string;
  type?: "line" | "bar";
  color?: string;
}

export default function Chart({
  labels,
  values,
  title,
  type = "line",
  color = "rgba(99,102,241,1)",
}: Props) {
  const data = {
    labels,
    datasets: [
      {
        label: title || "Series",
        data: values,
        borderColor: color,
        backgroundColor: type === "bar" ? color + "88" : color + "20",
        fill: type === "line",
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: color,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: !!title,
        labels: { color: "#e0e0e0" },
      },
      title: {
        display: !!title,
        text: title || "",
        color: "#f0f0f5",
      },
    },
    scales: {
      x: {
        ticks: { color: "#8888a0", maxRotation: 45 },
        grid: { color: "#2a2a3e" },
      },
      y: {
        ticks: { color: "#8888a0" },
        grid: { color: "#2a2a3e" },
      },
    },
  };

  const ChartComponent = type === "bar" ? Bar : Line;

  return (
    <div style={{ height: 300 }}>
      <ChartComponent data={data} options={options} />
    </div>
  );
}
