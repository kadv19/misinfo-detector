export default function Sidebar({ isOpen, toggle }) {
  return (
    <div
      className={`fixed right-0 top-0 h-full bg-[#2C2C2C] w-64 transform ${
        isOpen ? "translate-x-0" : "translate-x-full"
      } transition-transform duration-300 shadow-lg z-50`}
    >
      <button
        onClick={toggle}
        className="absolute left-4 top-4 text-white text-lg"
      >
        ✕
      </button>
      <ul className="mt-20 text-gray-300 space-y-6 px-8">
        <li className="hover:text-orange-400 cursor-pointer">Dashboard</li>
        <li className="hover:text-orange-400 cursor-pointer">Upload</li>
        <li className="hover:text-orange-400 cursor-pointer">Results</li>
        <li className="hover:text-orange-400 cursor-pointer">Settings</li>
      </ul>
    </div>
  );
}
