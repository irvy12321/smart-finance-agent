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
  color = "#5b9dff",
}: Props) {
  const barColors = ["#5b9dff", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899"];
  const data = {
    labels,
    datasets: [
      {
        label: title || "Series",
        data: values,
        borderColor: type === "bar" ? barColors : color,
        backgroundColor: type === "bar" ? labels.map((_, index) => barColors[index % barColors.length]) : color,
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
