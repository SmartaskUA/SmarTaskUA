import React from 'react'

function Home() {
  return (
    <div className="min-h-screen bg-base-200">
      <div className="navbar bg-base-100 shadow-lg">
        <div className="flex-1">
          <a className="btn btn-ghost text-xl">JSON Generator v2.2</a>
        </div>
      </div>

      <div className="container mx-auto p-8">
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title text-3xl">Welcome to JSON Generator</h2>
            <p className="text-lg">
              Generate JSON + CSV pairs for schema v2.2 more easily
            </p>
            <div className="divider"></div>
            <div className="alert alert-info">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>Infrastructure is ready! Start building your UI tomorrow.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
